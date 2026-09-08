"""Storage and aggregation contracts for Perception comment intelligence.

This module intentionally contains no LLM/provider integration. It defines the
normalized result shape that a future analysis worker can write and the
aggregate shape that the Perception intelligence API can safely expose.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, CommentIntelligence, Perception

SEMANTIC_SAMPLE_MINIMUM = 5
ALLOWED_SENTIMENTS = {"positive", "negative", "neutral", "mixed", "unclear"}
ALLOWED_STANCES = {"supportive", "challenging", "mixed", "unclear"}


def _distribution(values: Iterable[str | None]) -> list[dict]:
    counts = Counter(value for value in values if value)
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {
            "label": label,
            "comments": count,
            "share": round(count / total, 3),
        }
        for label, count in counts.most_common()
    ]


def _theme_distribution(rows: Iterable[CommentIntelligence]) -> list[dict]:
    counts: Counter[str] = Counter()
    for row in rows:
        for theme in row.themes or []:
            label = str(theme).strip()
            if label:
                counts[label] += 1
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {"theme": label, "comments": count, "share": round(count / total, 3)}
        for label, count in counts.most_common(10)
    ]


def _validate_analysis_payload(
    *,
    sentiment: str | None,
    stance: str | None,
    quality_score: float | None,
) -> None:
    if sentiment is not None and sentiment not in ALLOWED_SENTIMENTS:
        raise ValueError(f"Unsupported sentiment: {sentiment}")
    if stance is not None and stance not in ALLOWED_STANCES:
        raise ValueError(f"Unsupported stance: {stance}")
    if quality_score is not None and not 0.0 <= quality_score <= 1.0:
        raise ValueError("quality_score must be between 0 and 1")


async def upsert_comment_intelligence(
    db: AsyncSession,
    *,
    comment_id: int,
    status: str,
    sentiment: str | None = None,
    stance: str | None = None,
    themes: list[str] | None = None,
    is_question: bool = False,
    has_concern: bool = False,
    agreement_signal: bool = False,
    disagreement_signal: bool = False,
    quality_score: float | None = None,
    model_version: str | None = None,
    analyzed_at: datetime | None = None,
    error_code: str | None = None,
) -> CommentIntelligence:
    """Store one normalized analysis result for a comment.

    Intended for a future background analysis worker. This function does not
    call an AI provider and does not expose comment text or model prompts.
    """
    if status not in {"pending", "analyzed", "failed"}:
        raise ValueError(f"Unsupported analysis status: {status}")
    _validate_analysis_payload(
        sentiment=sentiment, stance=stance, quality_score=quality_score
    )
    clean_themes = [str(theme).strip() for theme in (themes or []) if str(theme).strip()]
    clean_themes = list(dict.fromkeys(clean_themes))[:10]

    existing = await db.scalar(
        select(CommentIntelligence).where(CommentIntelligence.comment_id == comment_id)
    )
    if existing is None:
        existing = CommentIntelligence(comment_id=comment_id)
        db.add(existing)

    existing.status = status
    existing.sentiment = sentiment
    existing.stance = stance
    existing.themes = clean_themes
    existing.is_question = is_question
    existing.has_concern = has_concern
    existing.agreement_signal = agreement_signal
    existing.disagreement_signal = disagreement_signal
    existing.quality_score = quality_score
    existing.model_version = model_version
    existing.analyzed_at = analyzed_at
    existing.error_code = error_code
    await db.flush()
    return existing


async def get_comment_intelligence_rows(
    db: AsyncSession,
    perception_id: int,
    since: datetime,
) -> list[CommentIntelligence]:
    """Return analyzed comment rows in the selected perception/time window."""
    result = await db.execute(
        select(CommentIntelligence)
        .join(Comment, Comment.id == CommentIntelligence.comment_id)
        .where(
            Comment.perception_id == perception_id,
            Comment.created_at >= since,
            CommentIntelligence.status == "analyzed",
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


def aggregate_comment_intelligence(
    rows: list[CommentIntelligence],
    *,
    period_days: int,
    minimum: int = SEMANTIC_SAMPLE_MINIMUM,
) -> dict:
    """Build a privacy-safe semantic aggregate from analyzed comment rows.

    This function never fabricates labels. If fewer than ``minimum`` analyzed
    comments exist, semantic interpretation is suppressed.
    """
    analyzed_count = len(rows)
    if analyzed_count < minimum:
        return {
            "semantic_analysis_status": "insufficient_sample",
            "semantic_analysis_note": (
                f"Semantic intelligence is withheld until at least {minimum} "
                "comments have been analyzed."
            ),
            "semantic_sample_minimum": minimum,
            "analyzed_comment_count": analyzed_count,
            "semantic_period_days": period_days,
            "semantic_quality_score": None,
            "sentiment_distribution": [],
            "stance_distribution": [],
            "top_themes": [],
            "question_count": 0,
            "concern_themes": [],
            "agreement_themes": [],
            "disagreement_themes": [],
        }

    quality_values = [row.quality_score for row in rows if row.quality_score is not None]
    quality = round(sum(quality_values) / len(quality_values), 3) if quality_values else None

    concern_themes = _theme_distribution(
        [row for row in rows if row.has_concern]
    )
    agreement_themes = _theme_distribution(
        [row for row in rows if row.agreement_signal]
    )
    disagreement_themes = _theme_distribution(
        [row for row in rows if row.disagreement_signal]
    )

    return {
        "semantic_analysis_status": "available",
        "semantic_analysis_note": "Aggregate semantic signals from analyzed comments.",
        "semantic_sample_minimum": minimum,
        "analyzed_comment_count": analyzed_count,
        "semantic_period_days": period_days,
        "semantic_quality_score": quality,
        "sentiment_distribution": _distribution(row.sentiment for row in rows),
        "stance_distribution": _distribution(row.stance for row in rows),
        "top_themes": _theme_distribution(rows),
        "question_count": sum(1 for row in rows if row.is_question),
        "concern_themes": concern_themes,
        "agreement_themes": agreement_themes,
        "disagreement_themes": disagreement_themes,
    }


async def process_pending_comment_intelligence() -> int:
    """Analyze a bounded batch of pending text comments.

    The worker stores only normalized semantic output. Provider failures are
    represented by safe error codes; raw provider responses are never stored.
    """
    import logging
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.models.models import Comment, CommentIntelligence, Perception
    from app.services.comment_intelligence_provider import (
        CommentIntelligenceProviderError,
        analyze_comment,
    )

    settings = get_settings()
    logger = logging.getLogger("comment_intelligence")
    if not settings.COMMENT_INTELLIGENCE_ENABLED:
        return 0
    if not settings.OPENAI_API_KEY:
        logger.warning("Comment intelligence enabled but OPENAI_API_KEY is not configured")
        return 0

    async with AsyncSessionLocal() as db:
        batch_size = max(1, settings.COMMENT_INTELLIGENCE_BATCH_SIZE)

        # Backfill comments created before the semantic layer existed.
        missing_result = await db.execute(
            select(Comment)
            .outerjoin(CommentIntelligence, CommentIntelligence.comment_id == Comment.id)
            .where(CommentIntelligence.id.is_(None))
            .order_by(Comment.created_at.asc())
            .limit(batch_size)
        )
        missing_comments = list(missing_result.scalars().all())
        for missing_comment in missing_comments:
            db.add(CommentIntelligence(comment_id=missing_comment.id, status="pending"))
        if missing_comments:
            await db.flush()

        result = await db.execute(
            select(Comment)
            .join(CommentIntelligence, CommentIntelligence.comment_id == Comment.id)
            .where(CommentIntelligence.status == "pending")
            .options(selectinload(Comment.perception).selectinload(Perception.topic))
            .order_by(Comment.created_at.asc())
            .limit(batch_size)
        )
        comments = list(result.scalars().all())

        processed = 0
        for comment in comments:
            intelligence = await db.scalar(
                select(CommentIntelligence).where(CommentIntelligence.comment_id == comment.id)
            )
            if intelligence is None or intelligence.status != "pending":
                continue

            if not comment.body or not comment.body.strip():
                intelligence.status = "failed"
                intelligence.error_code = "no_text"
                intelligence.model_version = settings.COMMENT_INTELLIGENCE_MODEL
                processed += 1
                continue

            try:
                result_payload = await analyze_comment(
                    comment_body=comment.body,
                    perception_body=comment.perception.body,
                    topic_name=comment.perception.topic.name if comment.perception.topic else None,
                )
                _validate_analysis_payload(
                    sentiment=result_payload.get("sentiment"),
                    stance=result_payload.get("stance"),
                    quality_score=result_payload.get("quality_score"),
                )
                await upsert_comment_intelligence(
                    db,
                    comment_id=comment.id,
                    status="analyzed",
                    sentiment=result_payload.get("sentiment"),
                    stance=result_payload.get("stance"),
                    themes=result_payload.get("themes") or [],
                    is_question=bool(result_payload.get("is_question")),
                    has_concern=bool(result_payload.get("has_concern")),
                    agreement_signal=bool(result_payload.get("agreement_signal")),
                    disagreement_signal=bool(result_payload.get("disagreement_signal")),
                    quality_score=float(result_payload.get("quality_score")),
                    model_version=settings.COMMENT_INTELLIGENCE_MODEL,
                    analyzed_at=datetime.now(timezone.utc),
                    error_code=None,
                )
                processed += 1
            except CommentIntelligenceProviderError as exc:
                if exc.code in {"provider_not_configured", "provider_timeout", "provider_request_error"}:
                    # Keep transient/configuration failures retryable.
                    logger.warning("Comment %s remains pending: %s", comment.id, exc.code)
                    continue
                intelligence.status = "failed"
                intelligence.error_code = exc.code
                intelligence.model_version = settings.COMMENT_INTELLIGENCE_MODEL
                processed += 1
            except (TypeError, ValueError) as exc:
                logger.warning("Comment %s produced invalid semantic output: %s", comment.id, exc.__class__.__name__)
                intelligence.status = "failed"
                intelligence.error_code = "invalid_analysis"
                intelligence.model_version = settings.COMMENT_INTELLIGENCE_MODEL
                processed += 1

        await db.commit()
        return processed
