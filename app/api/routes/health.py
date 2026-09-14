# app/api/routes/health.py
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/health")
async def health(db: DbSession, response: Response):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Health check database dependency unavailable: %s", type(exc).__name__
        )
        db_ok = False

    redis_ok = True
    try:
        async with Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            await redis.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Health check Redis dependency unavailable: %s", type(exc).__name__
        )
        redis_ok = False

    if not db_ok or not redis_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "redis": "ok" if redis_ok else "unreachable",
        "time": datetime.now(timezone.utc).isoformat(),
    }
