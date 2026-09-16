from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Follow, Perception, PerceptionModeration, Topic, TopicFollow, User
from app.schemas.recommendations import (
    CreatorRecommendation,
    PerceptionRecommendation,
    RecommendationsOut,
    TopicRecommendation,
)
from app.services.personalization import build_personalization_profile, score_perception
from app.services.privacy_contract_guard import creator_discoverability_allowed
from app.services.perception_serialization import bulk_to_out


def _topic_reason(score: float, *, interacted: bool, role_match: bool, geo_match: bool) -> str:
    if interacted:
        return "Related to topics you have engaged with."
    if role_match:
        return "Relevant to your professional context."
    if geo_match:
        return "Relevant to your public geographic context."
    if score > 0:
        return "Appears in recent perceptions relevant to you."
    return "A topic you may want to explore."


def _creator_reason(score: float, *, role_match: bool, geo_match: bool) -> str:
    if role_match and geo_match:
        return "Shares your professional context and public region."
    if role_match:
        return "Shares your professional context."
    if geo_match:
        return "Shares your public geographic context."
    return "Creates perceptions related to your interests."


async def get_recommendations(
    db: AsyncSession,
    user: User,
    *,
    topic_limit: int = 5,
    creator_limit: int = 5,
    perception_limit: int = 5,
) -> RecommendationsOut:
    profile = await build_personalization_profile(db, user)
    now = datetime.now(timezone.utc)

    followed_topic_ids = set(profile.followed_topic_ids)
    followed_user_ids = set(profile.followed_user_ids) | {user.id}

    # A bounded recent pool is sufficient for explainable recommendations and
    # avoids a request-path recommendation engine or popularity query.
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
        .limit(300)
    )
    perceptions = list(result.scalars().all())
    scored = [(p, score_perception(p, profile, now)) for p in perceptions]
    scored.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)

    topic_scores: dict[int, float] = {}
    creator_scores: dict[int, float] = {}
    topic_meta: dict[int, tuple[Topic, bool, bool]] = {}
    creator_meta: dict[int, tuple[User, bool, bool]] = {}

    for perception, score in scored:
        topic = perception.topic
        author = perception.user
        if topic is not None and topic.id not in followed_topic_ids:
            interacted = topic.id in profile.interacted_topic_scores
            role_match = False
            geo_match = False
            if author is not None:
                role_match = bool(profile.role and author.primary_professional_role == profile.role)
                if author.location_visibility in {"country", "region"}:
                    geo_match = bool(
                        profile.country_code
                        and author.country_code == profile.country_code
                        and (
                            author.location_visibility == "country"
                            or not profile.region
                            or not author.region
                            or author.region.casefold() == profile.region.casefold()
                        )
                    )
            topic_scores[topic.id] = max(topic_scores.get(topic.id, 0.0), score)
            topic_meta[topic.id] = (topic, interacted, role_match or geo_match)

        if (
            author is not None
            and author.id not in followed_user_ids
            and creator_discoverability_allowed(author)
        ):
            role_match = bool(profile.role and author.primary_professional_role == profile.role)
            geo_match = bool(
                author.location_visibility in {"country", "region"}
                and profile.country_code
                and author.country_code == profile.country_code
                and (
                    author.location_visibility == "country"
                    or not profile.region
                    or not author.region
                    or author.region.casefold() == profile.region.casefold()
                )
            )
            creator_scores[author.id] = max(creator_scores.get(author.id, 0.0), score)
            creator_meta[author.id] = (author, role_match, geo_match)

    top_topics = sorted(topic_scores.items(), key=lambda item: item[1], reverse=True)[:topic_limit]
    top_creators = sorted(creator_scores.items(), key=lambda item: item[1], reverse=True)[:creator_limit]

    topic_ids = [topic_id for topic_id, _ in top_topics]
    topic_counts: dict[int, int] = {}
    if topic_ids:
        from app.models.models import TopicFollow
        counts = await db.execute(
            select(TopicFollow.topic_id)
            .where(TopicFollow.topic_id.in_(topic_ids))
        )
        for topic_id in counts.scalars().all():
            topic_counts[topic_id] = topic_counts.get(topic_id, 0) + 1

    topics = [
        TopicRecommendation(
            reason=_topic_reason(score, interacted=topic_meta[topic_id][1], role_match=topic_meta[topic_id][2], geo_match=False),
            score=score,
            topic=(
                lambda t: t
            )(topic_meta[topic_id][0]),
        )
        for topic_id, score in top_topics
    ]
    # Replace follower counts with authoritative counts/state without exposing
    # any popularity value as a recommendation score.
    for item in topics:
        item.topic.followers_count = topic_counts.get(item.topic.id, 0)
        item.topic.followed_by_user = False

    creators = [
        CreatorRecommendation(
            reason=_creator_reason(score, role_match=creator_meta[creator_id][1], geo_match=creator_meta[creator_id][2]),
            score=score,
            creator=creator_meta[creator_id][0],
        )
        for creator_id, score in top_creators
    ]

    recommended_perceptions = [
        (p, score)
        for p, score in scored
        if p.user_id not in followed_user_ids
        and (p.topic_id not in followed_topic_ids or p.topic_id is None)
    ][:perception_limit]
    perception_models = await bulk_to_out(
        db, [p for p, _ in recommended_perceptions], user.id
    )
    perception_recommendations = [
        PerceptionRecommendation(
            reason="Recommended from your topics, professional context, and recent interests.",
            score=score,
            perception=perception,
        )
        for perception, (_, score) in zip(perception_models, recommended_perceptions)
    ]

    return RecommendationsOut(
        topics=topics,
        creators=creators,
        perceptions=perception_recommendations,
    )
