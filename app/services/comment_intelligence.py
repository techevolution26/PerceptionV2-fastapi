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

from app.models.models import Comment, CommentIntelligence, User

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
        .join(User, User.id == Comment.user_id)
        .where(
            Comment.perception_id == perception_id,
            Comment.created_at >= since,
            CommentIntelligence.status == "analyzed",
            User.is_active.is_(True),
            User.privacy_preferences["intelligence_participation"].as_boolean().is_not(False),
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def get_comment_intelligence_temporal_rows(
    db: AsyncSession,
    perception_id: int,
    since: datetime,
) -> list[tuple[CommentIntelligence, datetime]]:
    """Return analyzed intelligence paired with the original comment time."""
    result = await db.execute(
        select(CommentIntelligence, Comment.created_at)
        .join(Comment, Comment.id == CommentIntelligence.comment_id)
        .join(User, User.id == Comment.user_id)
        .where(
            Comment.perception_id == perception_id,
            Comment.created_at >= since,
            CommentIntelligence.status == "analyzed",
            User.is_active.is_(True),
            User.privacy_preferences["intelligence_participation"].as_boolean().is_not(False),
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.all())


async def get_comment_intelligence_participant_rows(
    db: AsyncSession,
    perception_id: int,
    since: datetime,
) -> list[tuple[CommentIntelligence, User]]:
    """Return analyzed comments with participant attributes for cohort aggregation."""
    result = await db.execute(
        select(CommentIntelligence, User)
        .join(Comment, Comment.id == CommentIntelligence.comment_id)
        .join(User, User.id == Comment.user_id)
        .where(
            Comment.perception_id == perception_id,
            Comment.created_at >= since,
            CommentIntelligence.status == "analyzed",
            User.is_active.is_(True),
            User.privacy_preferences["intelligence_participation"].as_boolean().is_not(False),
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.all())


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
