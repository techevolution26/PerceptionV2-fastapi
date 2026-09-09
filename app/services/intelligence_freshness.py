"""Freshness and recalculation state for Perception Intelligence."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, CommentIntelligence


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def assess_intelligence_freshness(
    db: AsyncSession,
    perception_id: int,
    since: datetime,
) -> dict:
    """Determine whether stored comment intelligence reflects current comments.

    This is deliberately derived from source and analysis timestamps. It does
    not claim that a provider has completed recalculation; pending rows are the
    queue signal consumed by the analysis worker.
    """
    comments = list((await db.scalars(
        select(Comment)
        .where(Comment.perception_id == perception_id, Comment.created_at >= since)
    )).all())
    comment_ids = {comment.id for comment in comments}

    if not comment_ids:
        return {
            "status": "current",
            "recalculation_required": False,
            "source_comment_count": 0,
            "analyzed_comment_count": 0,
            "pending_comment_count": 0,
            "failed_comment_count": 0,
            "latest_source_at": None,
            "latest_analysis_at": None,
            "note": "No comments are present in the selected period.",
        }

    intelligence_rows = list((await db.scalars(
        select(CommentIntelligence).where(CommentIntelligence.comment_id.in_(comment_ids))
    )).all())
    by_comment = {row.comment_id: row for row in intelligence_rows}
    analyzed = [row for row in intelligence_rows if row.status == "analyzed" and row.analyzed_at]
    pending = [row for row in intelligence_rows if row.status == "pending"]
    failed = [row for row in intelligence_rows if row.status == "failed"]
    missing = [comment for comment in comments if comment.id not in by_comment]

    latest_source = max((_aware(comment.created_at) for comment in comments), default=None)
    latest_analysis = max((_aware(row.analyzed_at) for row in analyzed), default=None)
    needs_recalculation = bool(missing or pending or failed)
    if latest_source and (latest_analysis is None or latest_source > latest_analysis):
        needs_recalculation = True

    if missing or pending:
        status = "pending"
        note = "New or queued comments are awaiting semantic analysis."
    elif failed or needs_recalculation:
        status = "stale"
        note = "Stored intelligence is older than the current conversation and requires recalculation."
    else:
        status = "current"
        note = "Stored intelligence covers the current comments in the selected period."

    return {
        "status": status,
        "recalculation_required": needs_recalculation,
        "source_comment_count": len(comments),
        "analyzed_comment_count": len(analyzed),
        "pending_comment_count": len(pending) + len(missing),
        "failed_comment_count": len(failed),
        "latest_source_at": latest_source,
        "latest_analysis_at": latest_analysis,
        "note": note,
    }
