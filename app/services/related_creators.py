from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, CommentIntelligence, Follow, Perception, PerceptionModeration, Topic, User
from app.schemas.related_creators import RelatedCreator, RelatedCreatorsOut
from app.services.personalization import build_personalization_profile
from app.services.privacy_contract_guard import creator_discoverability_allowed

MIN_SEMANTIC_SAMPLE = 5
MIN_SEMANTIC_PARTICIPANTS = 5
CANDIDATE_LIMIT = 150



def _public_location_label(user: User) -> str | None:
    visibility = str((user.privacy_preferences or {}).get("location_visibility", "private"))
    country = (user.country_code or "").strip().upper()
    region = (user.region or "").strip()
    if visibility == "region" and country and region:
        return f"{country} · {region}"
    if visibility in {"country", "region"} and country:
        return country
    return None


async def _profile_counts(db: AsyncSession, user_id: int) -> dict[str, int]:
    from app.models.models import Follow, TopicFollow
    perceptions_count = (await db.execute(select(func.count()).select_from(Perception).where(Perception.user_id == user_id))).scalar_one()
    followers_count = (await db.execute(select(func.count()).select_from(Follow).where(Follow.followed_id == user_id))).scalar_one()
    following_count = (await db.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id))).scalar_one()
    topics_count = (await db.execute(select(func.count()).select_from(TopicFollow).where(TopicFollow.user_id == user_id))).scalar_one()
    return {"perceptions_count": int(perceptions_count), "followers_count": int(followers_count), "following_count": int(following_count), "topics_count": int(topics_count)}


def _themes(rows: list[CommentIntelligence]) -> set[str]:
    return {
        str(theme).strip().casefold()
        for row in rows
        for theme in (row.themes or [])
        if str(theme).strip()
    }


def _reason(
    *,
    on_source_topic: bool,
    shared_themes: int,
    shared_roles: int,
    viewer_affinity: bool,
    public_geography_match: bool,
) -> str:
    if on_source_topic and shared_themes:
        return "Discusses this topic and shares themes observed in its conversations."
    if on_source_topic and shared_roles:
        return "Discusses this topic from a related professional perspective."
    if shared_themes:
        return "Shares themes observed in conversations around this topic."
    if shared_roles:
        return "Connects through an overlapping professional perspective."
    if viewer_affinity:
        return "Related to your explicit topic and creator interests."
    if public_geography_match:
        return "Adds a related perspective from the same public broad region."
    return "Related through the perception and topic graph."


async def _source_semantics(
    db: AsyncSession, topic_id: int
) -> set[str]:
    result = await db.execute(
        select(Comment.user_id, CommentIntelligence)
        .join(CommentIntelligence, Comment.id == CommentIntelligence.comment_id)
        .join(Perception, Perception.id == Comment.perception_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.topic_id == topic_id,
            CommentIntelligence.status == "analyzed",
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
    )
    rows: list[CommentIntelligence] = []
    participants: set[int] = set()
    for user_id, row in result.all():
        rows.append(row)
        if user_id is not None:
            participants.add(user_id)
    if len(rows) < MIN_SEMANTIC_SAMPLE or len(participants) < MIN_SEMANTIC_PARTICIPANTS:
        return set()
    return _themes(rows)


async def _creator_semantics(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, set[str]]:
    if not user_ids:
        return {}
    result = await db.execute(
        select(Perception.user_id, Comment.user_id, CommentIntelligence)
        .join(Comment, Comment.perception_id == Perception.id)
        .join(CommentIntelligence, Comment.id == CommentIntelligence.comment_id)
        .where(
            Perception.user_id.in_(user_ids),
            CommentIntelligence.status == "analyzed",
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
    )
    rows_by_creator: dict[int, list[CommentIntelligence]] = defaultdict(list)
    participants_by_creator: dict[int, set[int]] = defaultdict(set)
    for creator_id, participant_id, row in result.all():
        rows_by_creator[creator_id].append(row)
        if participant_id is not None:
            participants_by_creator[creator_id].add(participant_id)

    themes: dict[int, set[str]] = {}
    for creator_id, rows in rows_by_creator.items():
        participants = participants_by_creator.get(creator_id, set())
        if len(rows) >= MIN_SEMANTIC_SAMPLE and len(participants) >= MIN_SEMANTIC_PARTICIPANTS:
            themes[creator_id] = _themes(rows)
    return themes


def _profile_payload(user: User, counts: dict[str, int], following: bool) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "profession": user.profession,
        "verification_status": user.verification_status,
        "verification_badge": user.verification_badge,
        "professional_industries": list(user.professional_industries or []),
        "professional_roles": list(user.professional_roles or []),
        "primary_professional_role": user.primary_professional_role,
        "primary_professional_industry": user.primary_professional_industry,
        "primary_professional_role_label": user.primary_professional_role_label,
        "professional_role_labels": user.professional_role_labels,
        "verified_professional_roles": list(user.verified_professional_roles or []),
        "location_label": _public_location_label(user),
        "created_at": user.created_at,
        "is_following": following,
        "can_message": False,
        **counts,
    }


async def get_related_creators(
    db: AsyncSession,
    topic_id: int,
    viewer_id: int | None,
    *,
    limit: int = 5,
) -> RelatedCreatorsOut:
    limit = max(1, min(limit, 10))

    source = await db.scalar(select(Topic.id).where(Topic.id == topic_id))
    if source is None:
        return RelatedCreatorsOut(source_topic_id=topic_id, items=[])

    # Candidate discovery is based on active authorship, not follower or
    # engagement counts. The bounded recent pool also prevents an unbounded
    # semantic request path.
    candidate_result = await db.execute(
        select(User, Perception.created_at)
        .join(Perception, Perception.user_id == User.id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            User.is_active.is_(True),
            User.privacy_preferences["creator_discoverability"].as_boolean().is_not(False),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .order_by(Perception.created_at.desc())
        .limit(CANDIDATE_LIMIT)
    )
    candidate_rows = candidate_result.all()

    # Always retain every active creator currently contributing to the source
    # topic, then add a bounded recent pool for contextual discovery.
    source_result = await db.execute(
        select(User)
        .join(Perception, Perception.user_id == User.id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.topic_id == topic_id,
            User.is_active.is_(True),
            User.privacy_preferences["creator_discoverability"].as_boolean().is_not(False),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .distinct()
    )
    source_users = list(source_result.scalars().all())

    candidate_users: dict[int, User] = {user.id: user for user in source_users}
    latest_by_creator: dict[int, datetime] = {}
    source_topic_creators: set[int] = {user.id for user in source_users}
    for user, created_at in candidate_rows:
        candidate_users[user.id] = user
        latest_by_creator[user.id] = max(latest_by_creator.get(user.id, created_at), created_at)

    if not candidate_users:
        return RelatedCreatorsOut(source_topic_id=topic_id, items=[])

    candidate_ids = list(candidate_users)
    source_creator_dates = await db.execute(
        select(Perception.user_id, func.max(Perception.created_at))
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.topic_id == topic_id,
            Perception.user_id.in_(candidate_ids),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .group_by(Perception.user_id)
    )
    for creator_id, created_at in source_creator_dates.all():
        if created_at is not None:
            latest_by_creator[creator_id] = max(latest_by_creator.get(creator_id, created_at), created_at)

    source_themes = await _source_semantics(db, topic_id)
    creator_themes = await _creator_semantics(db, candidate_ids)

    source_roles_result = await db.execute(
        select(User.primary_professional_role)
        .join(Perception, Perception.user_id == User.id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.topic_id == topic_id,
            User.is_active.is_(True),
            User.privacy_preferences["creator_discoverability"].as_boolean().is_not(False),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
            User.primary_professional_role.is_not(None),
        )
        .distinct()
    )
    source_roles = {role for role in source_roles_result.scalars().all() if role}

    profile = None
    if viewer_id is not None:
        viewer = await db.scalar(select(User).where(User.id == viewer_id, User.is_active.is_(True)))
        if viewer is not None:
            profile = await build_personalization_profile(db, viewer)

    followed_creator_ids: set[int] = set()
    if viewer_id is not None:
        followed_result = await db.execute(
            select(Follow.followed_id).where(
                Follow.follower_id == viewer_id,
                Follow.followed_id.in_(candidate_ids),
            )
        )
        followed_creator_ids = set(followed_result.scalars().all())

    now = datetime.now(timezone.utc)
    scored: list[tuple[User, float, str]] = []
    for creator_id, creator in candidate_users.items():
        if creator_id == viewer_id or creator_id in followed_creator_ids:
            continue

        on_source_topic = creator_id in source_topic_creators
        shared_themes = len(source_themes & creator_themes.get(creator_id, set()))
        shared_roles = int(bool(source_roles and creator.primary_professional_role in source_roles))
        viewer_affinity = bool(
            profile
            and (
                creator_id in profile.followed_user_ids
                or profile.industry == creator.primary_professional_industry
                or profile.role == creator.primary_professional_role
            )
        )

        public_geography_match = False
        if profile and creator.location_visibility in {"country", "region"}:
            public_geography_match = bool(
                profile.country_code
                and creator.country_code == profile.country_code
            )
            if (
                public_geography_match
                and creator.location_visibility == "region"
                and profile.region
                and creator.region
            ):
                public_geography_match = creator.region.casefold() == profile.region.casefold()

        score = 0.0
        if on_source_topic:
            score += 5.0
        if shared_themes:
            score += min(6.0, shared_themes * 2.0)
        if shared_roles:
            score += 2.0
        if viewer_affinity:
            score += 2.0
        if public_geography_match:
            score += 1.0

        latest = latest_by_creator.get(creator_id)
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
                creator,
                score,
                _reason(
                    on_source_topic=on_source_topic,
                    shared_themes=shared_themes,
                    shared_roles=shared_roles,
                    viewer_affinity=viewer_affinity,
                    public_geography_match=public_geography_match,
                ),
            )
        )

    scored.sort(key=lambda item: (item[1], item[0].name.casefold()), reverse=True)
    selected = scored[:limit]

    items: list[RelatedCreator] = []
    for creator, score, reason in selected:
        counts = await _profile_counts(db, creator.id)
        following = creator.id in followed_creator_ids
        items.append(
            RelatedCreator(
                reason=reason,
                score=score,
                creator=_profile_payload(creator, counts, following),
            )
        )

    return RelatedCreatorsOut(source_topic_id=topic_id, items=items)
