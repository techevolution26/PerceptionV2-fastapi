from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, CommentIntelligence, Perception, Topic, TopicFollow, User
from app.schemas.related_topics import RelatedTopic, RelatedTopicsOut
from app.services.personalization import build_personalization_profile

MIN_SEMANTIC_SAMPLE = 5
MIN_SEMANTIC_PARTICIPANTS = 5
MIN_SHARED_CONTRIBUTORS = 2
CANDIDATE_LIMIT = 100


def _themes(rows: list[CommentIntelligence]) -> set[str]:
    return {
        str(theme).strip().casefold()
        for row in rows
        for theme in (row.themes or [])
        if str(theme).strip()
    }


def _reason(
    *,
    shared_contributors: int,
    shared_themes: int,
    shared_roles: int,
    viewer_affinity: bool,
) -> str:
    if shared_themes >= 2 and shared_contributors >= MIN_SHARED_CONTRIBUTORS:
        return "Shares conversation themes and contributors with this topic."
    if shared_themes >= 1:
        return "Shares themes observed in conversations around this topic."
    if shared_contributors >= MIN_SHARED_CONTRIBUTORS and shared_roles:
        return "Connects through overlapping contributors and professional lenses."
    if shared_contributors >= MIN_SHARED_CONTRIBUTORS:
        return "Connects through contributors who discuss both topics."
    if shared_roles:
        return "Connects through overlapping professional perspectives."
    if viewer_affinity:
        return "Related to topics you have explicitly engaged with."
    return "Related through the perception and topic graph."


async def _topic_participants(
    db: AsyncSession, topic_ids: list[int]
) -> dict[int, set[int]]:
    if not topic_ids:
        return {}
    result = await db.execute(
        select(Perception.topic_id, Perception.user_id)
        .join(User, User.id == Perception.user_id)
        .where(
            Perception.topic_id.in_(topic_ids),
            User.is_active.is_(True),
        )
        .distinct()
    )
    participants: dict[int, set[int]] = defaultdict(set)
    for topic_id, user_id in result.all():
        if topic_id is not None:
            participants[topic_id].add(user_id)
    return participants


async def _topic_roles(
    db: AsyncSession, topic_ids: list[int]
) -> dict[int, set[str]]:
    if not topic_ids:
        return {}
    result = await db.execute(
        select(Perception.topic_id, User.primary_professional_role)
        .join(User, User.id == Perception.user_id)
        .where(
            Perception.topic_id.in_(topic_ids),
            User.is_active.is_(True),
            User.primary_professional_role.is_not(None),
        )
        .distinct()
    )
    roles: dict[int, set[str]] = defaultdict(set)
    for topic_id, role in result.all():
        if topic_id is not None and role:
            roles[topic_id].add(role)
    return roles


async def _topic_semantics(
    db: AsyncSession, topic_ids: list[int]
) -> tuple[dict[int, set[str]], dict[int, set[int]]]:
    if not topic_ids:
        return {}, {}
    result = await db.execute(
        select(Perception.topic_id, Comment.user_id, CommentIntelligence)
        .join(Comment, Comment.perception_id == Perception.id)
        .join(CommentIntelligence, Comment.id == CommentIntelligence.comment_id)
        .where(
            Perception.topic_id.in_(topic_ids),
            CommentIntelligence.status == "analyzed",
        )
    )
    rows_by_topic: dict[int, list[CommentIntelligence]] = defaultdict(list)
    participants_by_topic: dict[int, set[int]] = defaultdict(set)
    for topic_id, user_id, row in result.all():
        if topic_id is None:
            continue
        rows_by_topic[topic_id].append(row)
        if user_id is not None:
            participants_by_topic[topic_id].add(user_id)

    themes: dict[int, set[str]] = {}
    qualified_participants: dict[int, set[int]] = {}
    for topic_id, rows in rows_by_topic.items():
        participants = participants_by_topic.get(topic_id, set())
        if len(rows) >= MIN_SEMANTIC_SAMPLE and len(participants) >= MIN_SEMANTIC_PARTICIPANTS:
            themes[topic_id] = _themes(rows)
            qualified_participants[topic_id] = participants
    return themes, qualified_participants


async def get_related_topics(
    db: AsyncSession,
    topic_id: int,
    viewer_id: int | None,
    *,
    limit: int = 5,
) -> RelatedTopicsOut:
    limit = max(1, min(limit, 10))

    source = await db.scalar(select(Topic).where(Topic.id == topic_id))
    if source is None:
        return RelatedTopicsOut(source_topic_id=topic_id, items=[])

    candidate_result = await db.execute(
        select(Topic)
        .join(Perception, Perception.topic_id == Topic.id)
        .join(User, User.id == Perception.user_id)
        .where(
            Topic.id != topic_id,
            User.is_active.is_(True),
        )
        .group_by(Topic.id)
        .order_by(func.max(Perception.created_at).desc())
        .limit(CANDIDATE_LIMIT)
    )
    candidates = list(candidate_result.scalars().all())
    if not candidates:
        return RelatedTopicsOut(source_topic_id=topic_id, items=[])

    topic_ids = [topic.id for topic in candidates] + [topic_id]
    participants = await _topic_participants(db, topic_ids)
    roles = await _topic_roles(db, topic_ids)
    semantic_themes, _semantic_participants = await _topic_semantics(db, topic_ids)

    source_participants = participants.get(topic_id, set())
    source_roles = roles.get(topic_id, set())
    source_themes = semantic_themes.get(topic_id, set())

    followed_topic_ids: set[int] = set()
    interacted_topic_ids: set[int] = set()
    profile = None
    if viewer_id is not None:
        user = await db.scalar(select(User).where(User.id == viewer_id))
        if user is not None:
            profile = await build_personalization_profile(db, user)
            followed_topic_ids = set(profile.followed_topic_ids)
            interacted_topic_ids = set(profile.interacted_topic_scores)

    now = datetime.now(timezone.utc)
    latest_result = await db.execute(
        select(Perception.topic_id, func.max(Perception.created_at))
        .where(Perception.topic_id.in_([topic.id for topic in candidates]))
        .group_by(Perception.topic_id)
    )
    latest_by_topic = {topic_id: latest for topic_id, latest in latest_result.all() if topic_id is not None}

    scored: list[tuple[Topic, float, str]] = []
    for candidate in candidates:
        candidate_participants = participants.get(candidate.id, set())
        shared_contributors = len(source_participants & candidate_participants)

        candidate_roles = roles.get(candidate.id, set())
        shared_roles = len(source_roles & candidate_roles)

        candidate_themes = semantic_themes.get(candidate.id, set())
        shared_themes = len(source_themes & candidate_themes)

        score = 0.0
        if shared_contributors >= MIN_SHARED_CONTRIBUTORS:
            score += min(6.0, shared_contributors * 2.0)
        if shared_themes:
            score += min(6.0, shared_themes * 2.0)
        if shared_roles:
            score += min(2.0, shared_roles * 0.5)

        viewer_affinity = candidate.id in followed_topic_ids or candidate.id in interacted_topic_ids
        if candidate.id in interacted_topic_ids:
            score += 3.0
        elif candidate.id in followed_topic_ids:
            score += 2.0

        # A small recency tie-breaker keeps newly active topics discoverable
        # without turning global activity/popularity into the recommendation score.
        latest = latest_by_topic.get(candidate.id)
        if latest is not None:
            age_days = max(0.0, (now - latest).total_seconds() / 86400)
            if age_days <= 7:
                score += 1.0
            elif age_days <= 30:
                score += 0.5

        if score <= 0:
            continue

        scored.append(
            (
                candidate,
                score,
                _reason(
                    shared_contributors=shared_contributors,
                    shared_themes=shared_themes,
                    shared_roles=shared_roles,
                    viewer_affinity=viewer_affinity,
                ),
            )
        )

    scored.sort(key=lambda item: (item[1], item[0].name.casefold()), reverse=True)
    selected = scored[:limit]
    selected_ids = [topic.id for topic, _, _ in selected]

    follower_counts: dict[int, int] = {}
    if selected_ids:
        counts = await db.execute(
            select(TopicFollow.topic_id, func.count(TopicFollow.user_id))
            .where(TopicFollow.topic_id.in_(selected_ids))
            .group_by(TopicFollow.topic_id)
        )
        follower_counts = {topic_id: int(count) for topic_id, count in counts.all()}

    followed_by_user = set()
    if viewer_id is not None and selected_ids:
        followed = await db.execute(
            select(TopicFollow.topic_id).where(
                TopicFollow.user_id == viewer_id,
                TopicFollow.topic_id.in_(selected_ids),
            )
        )
        followed_by_user = set(followed.scalars().all())

    items: list[RelatedTopic] = []
    for topic, score, reason in selected:
        topic_out = {
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "image_url": topic.image_url,
            "followers_count": follower_counts.get(topic.id, 0),
            "followed_by_user": topic.id in followed_by_user,
        }
        items.append(RelatedTopic(reason=reason, score=score, topic=topic_out))

    return RelatedTopicsOut(source_topic_id=topic_id, items=items)
