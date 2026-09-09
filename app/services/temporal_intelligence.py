"""Deterministic temporal intelligence for Perception conversations."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from app.models.models import CommentIntelligence

TEMPORAL_SCHEMA_VERSION = "1.0"
TEMPORAL_BUCKET_DAYS = 7
MINIMUM_SAMPLE = 5


def _dist(values: list[str | None]) -> list[dict[str, Any]]:
    counts = Counter(v for v in values if v)
    total = sum(counts.values())
    return [{"label": k, "comments": v, "share": round(v / total, 3)} for k, v in counts.most_common()] if total else []


def _themes(rows: list[CommentIntelligence]) -> list[dict[str, Any]]:
    counts = Counter(str(t).strip() for r in rows for t in (r.themes or []) if str(t).strip())
    total = sum(counts.values())
    return [{"theme": k, "comments": v, "share": round(v / total, 3)} for k, v in counts.most_common(5)] if total else []


def build_temporal_intelligence(
    temporal_rows: list[tuple[CommentIntelligence, datetime]],
    *,
    period_start: datetime,
    period_end: datetime,
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Bucket analyzed responses by their actual comment creation time.

    A bucket is analytically visible only when it contains at least ``minimum``
    analyzed comments. Trends compare qualifying buckets only; no interpolation
    is performed for suppressed periods.
    """
    bucket_size = timedelta(days=TEMPORAL_BUCKET_DAYS)
    buckets: list[dict[str, Any]] = []
    cursor = period_start
    while cursor < period_end:
        end = min(cursor + bucket_size, period_end)
        rows = [row for row, created_at in temporal_rows if cursor <= created_at < end]
        sample = len(rows)
        available = sample >= minimum
        buckets.append({
            "period_start": cursor,
            "period_end": end,
            "sample_size": sample,
            "status": "available" if available else "insufficient_sample",
            "sentiment_distribution": _dist([r.sentiment for r in rows]) if available else [],
            "stance_distribution": _dist([r.stance for r in rows]) if available else [],
            "top_themes": _themes(rows) if available else [],
            "question_count": sum(1 for r in rows if r.is_question) if available else 0,
            "quality_score": (
                round(sum(r.quality_score for r in rows if r.quality_score is not None) / len([r for r in rows if r.quality_score is not None]), 3)
                if available and any(r.quality_score is not None for r in rows) else None
            ),
        })
        cursor = end

    qualifying = [b for b in buckets if b["status"] == "available"]
    changes: list[dict[str, Any]] = []
    for previous, current in zip(qualifying, qualifying[1:]):
        prev_stance = previous["stance_distribution"][0]["label"] if previous["stance_distribution"] else None
        curr_stance = current["stance_distribution"][0]["label"] if current["stance_distribution"] else None
        prev_theme = previous["top_themes"][0]["theme"] if previous["top_themes"] else None
        curr_theme = current["top_themes"][0]["theme"] if current["top_themes"] else None
        changes.append({
            "from_period_start": previous["period_start"],
            "to_period_end": current["period_end"],
            "sample_size_from": previous["sample_size"],
            "sample_size_to": current["sample_size"],
            "leading_stance_from": prev_stance,
            "leading_stance_to": curr_stance,
            "leading_theme_from": prev_theme,
            "leading_theme_to": curr_theme,
            "stance_changed": prev_stance != curr_stance,
            "theme_changed": prev_theme != curr_theme,
        })

    status = "available" if qualifying else "insufficient_sample"
    note = (
        f"Temporal intelligence uses {TEMPORAL_BUCKET_DAYS}-day response windows; only windows with at least {minimum} analyzed comments are shown as analytical evidence."
        if qualifying else
        f"Temporal intelligence is withheld until at least one {TEMPORAL_BUCKET_DAYS}-day window contains {minimum} analyzed comments."
    )
    return {
        "schema_version": TEMPORAL_SCHEMA_VERSION,
        "status": status,
        "bucket_days": TEMPORAL_BUCKET_DAYS,
        "sample_minimum": minimum,
        "qualifying_bucket_count": len(qualifying),
        "buckets": buckets,
        "changes": changes,
        "note": note,
        "limitations": [
            "Temporal association does not establish causation.",
            "Suppressed windows are not interpolated or treated as zero activity.",
            "Observed changes may reflect who participated rather than a change in the wider population.",
        ],
    }
