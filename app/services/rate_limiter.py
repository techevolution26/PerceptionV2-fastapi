import hashlib
import logging

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def enforce_rate_limit(
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int = 60,
    message: str,
) -> None:
    """Apply a small Redis-backed fixed-window limit to an authenticated action.

    Limits are keyed by a one-way digest rather than storing raw identifiers in
    Redis. Production fails closed when the limiter dependency is unavailable.
    """
    digest = hashlib.sha256(identity.strip().lower().encode()).hexdigest()
    key = f"abuse:{scope}:{digest}"
    try:
        async with Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            ttl = await redis.ttl(key)
    except Exception as exc:
        logger.warning(
            "Abuse rate-limit dependency unavailable: %s",
            type(exc).__name__,
            extra={"scope": scope},
        )
        if settings.RATE_LIMIT_FAIL_OPEN:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protection service temporarily unavailable. Please try again shortly.",
        ) from exc

    if count > limit:
        retry_after = max(1, ttl)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={"Retry-After": str(retry_after)},
        )
