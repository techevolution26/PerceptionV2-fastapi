"""Controlled background worker for comment semantic intelligence."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.models import Comment, CommentIntelligence, Perception
from app.services.comment_intelligence import upsert_comment_intelligence
from app.services.comment_intelligence_provider import (
    CommentIntelligenceProviderError,
    analyze_comment,
)

logger = logging.getLogger("comment_intelligence")

COOLDOWN_KEY = "comment-intelligence:provider-cooldown"
LOCK_KEY = "comment-intelligence:worker-lock"


async def _cooldown_remaining(redis: Redis) -> int:
    value = await redis.get(COOLDOWN_KEY)
    if value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


async def _set_cooldown(redis: Redis, seconds: int, maximum: int) -> int:
    bounded = max(1, min(seconds, maximum))
    await redis.set(COOLDOWN_KEY, str(bounded), ex=bounded)
    return bounded


async def _acquire_lock(redis: Redis, ttl_seconds: int) -> str | None:
    token = secrets.token_urlsafe(24)
    acquired = await redis.set(LOCK_KEY, token, nx=True, ex=max(30, ttl_seconds))
    return token if acquired else None


async def _release_lock(redis: Redis, token: str) -> None:
    current = await redis.get(LOCK_KEY)
    if current == token:
        await redis.delete(LOCK_KEY)


async def process_pending_comment_intelligence() -> int:
    """Process a bounded batch without ever running in a request path.

    Safety controls:
    - feature flag disabled by default;
    - Redis cooldown survives process restarts;
    - distributed Redis lock prevents duplicate workers across API replicas;
    - bounded batch size and one provider request per comment;
    - provider failures never expose raw responses to the database;
    - HTTP 429 immediately pauses the worker and leaves the comment pending.
    """
    settings = get_settings()
    if (
        not settings.COMMENT_INTELLIGENCE_ENABLED
        or not settings.OPENAI_API_KEY
        or not settings.COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED
    ):
        return 0

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        remaining = await _cooldown_remaining(redis)
        if remaining > 0:
            logger.info("Comment intelligence provider cooldown active: %ss", remaining)
            return 0

        batch_size = max(1, settings.COMMENT_INTELLIGENCE_BATCH_SIZE)
        lock_ttl = max(60, batch_size * 45)
        token = await _acquire_lock(redis, lock_ttl)
        if token is None:
            logger.info("Comment intelligence worker already active")
            return 0

        try:
            async with AsyncSessionLocal() as db:
                # Backfill comments created before the queue existed.
                missing_result = await db.execute(
                    select(Comment)
                    .outerjoin(
                        CommentIntelligence,
                        CommentIntelligence.comment_id == Comment.id,
                    )
                    .where(CommentIntelligence.id.is_(None))
                    .order_by(Comment.created_at.asc())
                    .limit(batch_size)
                )
                missing_comments = list(missing_result.scalars().all())
                for missing_comment in missing_comments:
                    db.add(
                        CommentIntelligence(
                            comment_id=missing_comment.id, status="pending"
                        )
                    )
                if missing_comments:
                    await db.flush()

                result = await db.execute(
                    select(Comment)
                    .join(
                        CommentIntelligence,
                        CommentIntelligence.comment_id == Comment.id,
                    )
                    .where(CommentIntelligence.status == "pending")
                    .options(
                        selectinload(Comment.perception).selectinload(Perception.topic)
                    )
                    .order_by(Comment.created_at.asc())
                    .limit(batch_size)
                )
                comments = list(result.scalars().all())
                processed = 0

                for comment in comments:
                    intelligence = await db.scalar(
                        select(CommentIntelligence).where(
                            CommentIntelligence.comment_id == comment.id
                        )
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
                            topic_name=(
                                comment.perception.topic.name
                                if comment.perception.topic
                                else None
                            ),
                        )
                        await upsert_comment_intelligence(
                            db,
                            comment_id=comment.id,
                            status="analyzed",
                            sentiment=result_payload["sentiment"],
                            stance=result_payload["stance"],
                            themes=result_payload["themes"],
                            is_question=result_payload["is_question"],
                            has_concern=result_payload["has_concern"],
                            agreement_signal=result_payload["agreement_signal"],
                            disagreement_signal=result_payload["disagreement_signal"],
                            quality_score=result_payload["quality_score"],
                            model_version=settings.COMMENT_INTELLIGENCE_MODEL,
                            analyzed_at=datetime.now(timezone.utc),
                            error_code=None,
                        )
                        processed += 1
                    except CommentIntelligenceProviderError as exc:
                        if exc.code == "provider_rate_limited":
                            retry_seconds = (
                                exc.retry_after_seconds
                                or settings.COMMENT_INTELLIGENCE_DEFAULT_COOLDOWN_SECONDS
                            )
                            cooldown = await _set_cooldown(
                                redis,
                                retry_seconds,
                                settings.COMMENT_INTELLIGENCE_MAX_COOLDOWN_SECONDS,
                            )
                            logger.warning(
                                "Comment intelligence provider rate-limited; cooldown=%ss",
                                cooldown,
                            )
                            break

                        if exc.code in {
                            "provider_not_configured",
                            "external_processing_not_allowed",
                            "provider_timeout",
                            "provider_request_error",
                            "provider_server_error",
                        }:
                            logger.warning(
                                "Comment %s remains pending: %s", comment.id, exc.code
                            )
                            continue

                        intelligence.status = "failed"
                        intelligence.error_code = exc.code
                        intelligence.model_version = settings.COMMENT_INTELLIGENCE_MODEL
                        processed += 1
                    except (TypeError, ValueError) as exc:
                        logger.warning(
                            "Comment %s produced invalid semantic output: %s",
                            comment.id,
                            exc.__class__.__name__,
                        )
                        intelligence.status = "failed"
                        intelligence.error_code = "invalid_analysis"
                        intelligence.model_version = settings.COMMENT_INTELLIGENCE_MODEL
                        processed += 1

                await db.commit()
                return processed
        finally:
            await _release_lock(redis, token)
    except Exception:
        logger.exception("Comment intelligence worker failed safely")
        return 0
    finally:
        await redis.aclose()
