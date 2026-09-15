from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    Comment,
    Follow,
    Like,
    Perception,
    SavedPerception,
    TopicFollow,
    User,
)


@dataclass(frozen=True)
class PersonalizationProfile:
    followed_topic_ids: frozenset[int]
    followed_user_ids: frozenset[int]
    interacted_topic_scores: dict[int, int]
    role: str | None
    industry: str | None
    country_code: str | None
    region: str | None


def _recency_score(created_at: datetime, now: datetime) -> float:
    age_days = max(0.0, (now - created_at).total_seconds() / 86400)
    if age_days <= 1:
        return 2.0
    if age_days <= 3:
        return 1.5
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.5
    return 0.0


def score_perception(
    perception: Perception,
    profile: PersonalizationProfile,
    now: datetime,
) -> float:
    """Score relevance from user context and explicit behavior only.

    This deliberately does not use the perception's global likes/comments/views
    counts. Those are popularity metrics, not personalization signals.
    """
    score = _recency_score(perception.created_at, now)

    if perception.topic_id in profile.followed_topic_ids:
        score += 6.0

    if perception.user_id in profile.followed_user_ids:
        score += 5.0

    if perception.topic_id is not None:
        score += float(profile.interacted_topic_scores.get(perception.topic_id, 0))

    author = perception.user
    if author is not None:
        if profile.role and author.primary_professional_role == profile.role:
            score += 3.0
        author_industry = author.primary_professional_industry
        if profile.industry and author_industry == profile.industry:
            score += 2.0

        # Geography is only a relevance signal when the creator has chosen to
        # make that broad context public. No city is ever used or exposed.
        if author.location_visibility in {"country", "region"}:
            if profile.country_code and author.country_code == profile.country_code:
                score += 1.0
                if (
                    author.location_visibility == "region"
                    and profile.region
                    and author.region
                    and author.region.casefold() == profile.region.casefold()
                ):
                    score += 2.0

    return score


async def build_personalization_profile(
    db: AsyncSession, user: User
) -> PersonalizationProfile:
    followed_topics = await db.scalars(
        select(TopicFollow.topic_id).where(TopicFollow.user_id == user.id)
    )
    followed_users = await db.scalars(
        select(Follow.followed_id).where(Follow.follower_id == user.id)
    )

    interacted_topic_scores: dict[int, int] = {}

    liked_topics = await db.scalars(
        select(Perception.topic_id)
        .join(Like, Like.perception_id == Perception.id)
        .where(Like.user_id == user.id, Perception.topic_id.is_not(None))
        .distinct()
    )
    for topic_id in liked_topics:
        if topic_id is not None:
            interacted_topic_scores[topic_id] = max(
                interacted_topic_scores.get(topic_id, 0), 2
            )

    saved_topics = await db.scalars(
        select(Perception.topic_id)
        .join(SavedPerception, SavedPerception.perception_id == Perception.id)
        .where(SavedPerception.user_id == user.id, Perception.topic_id.is_not(None))
        .distinct()
    )
    for topic_id in saved_topics:
        if topic_id is not None:
            interacted_topic_scores[topic_id] = max(
                interacted_topic_scores.get(topic_id, 0), 3
            )

    commented_topics = await db.scalars(
        select(Perception.topic_id)
        .join(Comment, Comment.perception_id == Perception.id)
        .where(Comment.user_id == user.id, Perception.topic_id.is_not(None))
        .distinct()
    )
    for topic_id in commented_topics:
        if topic_id is not None:
            interacted_topic_scores[topic_id] = max(
                interacted_topic_scores.get(topic_id, 0), 3
            )

    return PersonalizationProfile(
        followed_topic_ids=frozenset(followed_topics),
        followed_user_ids=frozenset(followed_users),
        interacted_topic_scores=interacted_topic_scores,
        role=user.primary_professional_role,
        industry=user.primary_professional_industry,
        country_code=user.country_code,
        region=user.region,
    )


async def get_personalized_perceptions(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 50,
) -> list[Perception]:
    """Return a bounded, context-aware feed from the recent candidate pool."""
    candidate_limit = max(limit * 4, 100)
    result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .where(User.is_active.is_(True))
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
        .limit(candidate_limit)
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return []

    profile = await build_personalization_profile(db, user)
    now = datetime.now(timezone.utc)

    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (
            score_perception(item[1], profile, now),
            item[1].created_at,
            -item[0],
        ),
        reverse=True,
    )
    return [perception for _, perception in ranked[:limit]]
