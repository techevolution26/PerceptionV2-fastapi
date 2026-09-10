"""Quality and governance metrics for AI-derived comment intelligence."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, CommentIntelligence

MINIMUM_SAMPLE = 5
LOW_QUALITY_THRESHOLD = 0.60


async def assess_intelligence_quality(
    db: AsyncSession,
    perception_id: int,
    since: datetime,
    *,
    minimum: int = MINIMUM_SAMPLE,
) -> dict:
    """Return privacy-safe quality/coverage metrics for a perception.

    Quality metrics describe the analysis pipeline, not the people who wrote
    the comments. No raw provider output, prompt, or participant identity is
    returned.
    """
    result = await db.execute(
        select(CommentIntelligence)
        .join(Comment, Comment.id == CommentIntelligence.comment_id)
        .where(
            Comment.perception_id == perception_id,
            Comment.created_at >= since,
        )
    )
    rows = list(result.scalars().all())

    analyzed = [row for row in rows if row.status == "analyzed"]
    pending = sum(1 for row in rows if row.status == "pending")
    failed = sum(1 for row in rows if row.status == "failed")
    quality_values = [float(row.quality_score) for row in analyzed if row.quality_score is not None]
    quality = round(sum(quality_values) / len(quality_values), 3) if quality_values else None
    low_quality = sum(value < LOW_QUALITY_THRESHOLD for value in quality_values)

    versions = Counter(
        str(row.model_version)
        for row in analyzed
        if row.model_version
    )
    model_versions = [
        {"model_version": version, "comments": count}
        for version, count in versions.most_common()
    ]

    available = len(analyzed) >= minimum
    return {
        "status": "available" if available else "not_ready",
        "analyzed_comment_count": len(analyzed),
        "quality_score": quality if available else None,
        "low_quality_comment_count": low_quality if available else 0,
        "low_quality_share": round(low_quality / len(quality_values), 3)
        if available and quality_values
        else None,
        "failed_comment_count": failed,
        "pending_comment_count": pending,
        "model_versions": model_versions if available else [],
        "note": (
            "Quality metrics are available for the analyzed conversation sample."
            if available
            else f"Quality metrics are withheld until at least {minimum} comments have been analyzed."
        ),
        "limitations": [
            "Quality score is a model-output quality indicator, not statistical confidence.",
            "Low-quality classifications are retained for auditability but are not treated as stronger evidence.",
            "Provider errors and pending analyses can make intelligence incomplete.",
            "Model quality does not establish that the underlying conversation is representative of a population.",
        ],
    }
