from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Comment, Follow, Like, Perception, SavedPerception, PerceptionModeration, TopicFollow, User


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
    """Score feed relevance from explicit context and behavior.

    This deliberately excludes global popularity metrics. The score answers
    "is this relevant to this person?", not "is this popular?".
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

        # Only explicitly public broad geography can contribute. City is never
        # used as a ranking signal.
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
            interacted_topic_scores[topic_id] = max(interacted_topic_scores.get(topic_id, 0), 2)

    saved_topics = await db.scalars(
        select(Perception.topic_id)
        .join(SavedPerception, SavedPerception.perception_id == Perception.id)
        .where(SavedPerception.user_id == user.id, Perception.topic_id.is_not(None))
        .distinct()
    )
    for topic_id in saved_topics:
        if topic_id is not None:
            interacted_topic_scores[topic_id] = max(interacted_topic_scores.get(topic_id, 0), 3)

    commented_topics = await db.scalars(
        select(Perception.topic_id)
        .join(Comment, Comment.perception_id == Perception.id)
        .where(Comment.user_id == user.id, Perception.topic_id.is_not(None))
        .distinct()
    )
    for topic_id in commented_topics:
        if topic_id is not None:
            interacted_topic_scores[topic_id] = max(interacted_topic_scores.get(topic_id, 0), 3)

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
    """Rank a bounded recent candidate pool for the current viewer.

    Ranking is intentionally viewer-specific. After relevance scoring, a
    small diversity constraint prevents one creator/topic from monopolizing
    the feed. This is not popularity suppression; it is exposure diversity.
    """
    limit = max(1, min(limit, 50))
    candidate_limit = max(limit * 6, 150)
    result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
        .limit(candidate_limit)
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return []

    profile = await build_personalization_profile(db, user)
    now = datetime.now(timezone.utc)
    scored = [
        (index, perception, score_perception(perception, profile, now))
        for index, perception in enumerate(candidates)
    ]
    scored.sort(key=lambda item: (item[2], item[1].created_at, -item[0]), reverse=True)

    # Diversity is applied after relevance so highly relevant followed topics
    # still surface first, but a single author/topic cannot fill the whole page.
    selected: list[Perception] = []
    deferred: list[tuple[int, Perception, float]] = []
    topic_counts: dict[int | None, int] = {}
    author_counts: dict[int, int] = {}

    for item in scored:
        _, perception, _ = item
        topic_count = topic_counts.get(perception.topic_id, 0)
        author_count = author_counts.get(perception.user_id, 0)
        if topic_count >= 4 or author_count >= 3:
            deferred.append(item)
            continue
        selected.append(perception)
        topic_counts[perception.topic_id] = topic_count + 1
        author_counts[perception.user_id] = author_count + 1
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for _, perception, _ in deferred:
            if perception.id in {item.id for item in selected}:
                continue
            selected.append(perception)
            if len(selected) >= limit:
                break

    return selected
