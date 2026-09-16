from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Comment, CommentIntelligence, Perception, PerceptionModeration, User
from app.schemas.related_perceptions import RelatedPerception, RelatedPerceptionsOut
from app.services.perception_serialization import bulk_to_out

MIN_SEMANTIC_SAMPLE = 5


def _themes(rows: list[CommentIntelligence]) -> set[str]:
    return {
        str(theme).strip().casefold()
        for row in rows
        for theme in (row.themes or [])
        if str(theme).strip()
    }


def _dominant_context(rows: list[CommentIntelligence]) -> tuple[str | None, str | None]:
    sentiments = Counter(row.sentiment for row in rows if row.sentiment)
    stances = Counter(row.stance for row in rows if row.stance)
    return (
        sentiments.most_common(1)[0][0] if sentiments else None,
        stances.most_common(1)[0][0] if stances else None,
    )


def _reason(
    *, same_topic: bool, shared_themes: int, role_match: bool, context_match: bool
) -> str:
    if shared_themes >= 2 and context_match:
        return "Shares themes and conversation context with this perception."
    if shared_themes >= 1:
        return "Shares themes observed in the conversation around this perception."
    if same_topic and role_match:
        return "Same topic and professional lens."
    if same_topic:
        return "Another perception on the same topic."
    if role_match:
        return "A related professional lens on this subject."
    return "Related context from recent perceptions."


async def get_related_perceptions(
    db: AsyncSession,
    perception_id: int,
    viewer_id: int | None,
    *,
    limit: int = 5,
) -> RelatedPerceptionsOut:
    limit = max(1, min(limit, 10))
    source_result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.id == perception_id,
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        return RelatedPerceptionsOut(source_perception_id=perception_id, items=[])

    source_rows_result = await db.execute(
        select(CommentIntelligence)
        .join(Comment, Comment.id == CommentIntelligence.comment_id)
        .where(
            Comment.perception_id == perception_id,
            CommentIntelligence.status == "analyzed",
        )
    )
    source_rows = list(source_rows_result.scalars().all())
    source_themes = _themes(source_rows) if len(source_rows) >= MIN_SEMANTIC_SAMPLE else set()
    source_sentiment, source_stance = _dominant_context(source_rows) if source_rows else (None, None)

    candidate_result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.id != perception_id,
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
        .limit(300)
    )
    candidates = list(candidate_result.scalars().all())
    if not candidates:
        return RelatedPerceptionsOut(source_perception_id=perception_id, items=[])

    candidate_ids = [candidate.id for candidate in candidates]
    intelligence_result = await db.execute(
        select(Comment.perception_id, CommentIntelligence)
        .join(CommentIntelligence, Comment.id == CommentIntelligence.comment_id)
        .where(
            Comment.perception_id.in_(candidate_ids),
            CommentIntelligence.status == "analyzed",
        )
    )
    rows_by_perception: dict[int, list[CommentIntelligence]] = {}
    for candidate_id, row in intelligence_result.all():
        rows_by_perception.setdefault(candidate_id, []).append(row)

    now = datetime.now(timezone.utc)
    scored: list[tuple[Perception, float, str]] = []
    for candidate in candidates:
        score = 0.0
        same_topic = source.topic_id is not None and candidate.topic_id == source.topic_id
        if same_topic:
            score += 5.0

        candidate_rows = rows_by_perception.get(candidate.id, [])
        candidate_themes = _themes(candidate_rows) if len(candidate_rows) >= MIN_SEMANTIC_SAMPLE else set()
        shared_themes = len(source_themes & candidate_themes)
        if source_themes and candidate_themes:
            score += min(6.0, shared_themes * 2.0)

        role_match = bool(
            source.user
            and candidate.user
            and source.user.primary_professional_role
            and source.user.primary_professional_role == candidate.user.primary_professional_role
        )
        if role_match:
            score += 2.0

        candidate_sentiment, candidate_stance = _dominant_context(candidate_rows) if candidate_rows else (None, None)
        context_match = bool(
            source_rows
            and candidate_rows
            and ((source_stance and candidate_stance == source_stance) or (source_sentiment and candidate_sentiment == source_sentiment))
        )
        if context_match:
            score += 1.5

        age_days = max(0.0, (now - candidate.created_at).total_seconds() / 86400)
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
                    same_topic=same_topic,
                    shared_themes=shared_themes,
                    role_match=role_match,
                    context_match=context_match,
                ),
            )
        )

    scored.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)
    selected = scored[:limit]
    models = await bulk_to_out(db, [item[0] for item in selected], viewer_id)
    items = [
        RelatedPerception(reason=reason, score=score, perception=model)
        for model, (_, score, reason) in zip(models, selected)
    ]
    return RelatedPerceptionsOut(source_perception_id=perception_id, items=items)
