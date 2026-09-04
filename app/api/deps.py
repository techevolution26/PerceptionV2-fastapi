from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User

DbSession = Annotated[AsyncSession, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


async def _resolve_user(db: AsyncSession, credentials: HTTPAuthorizationCredentials | None, *, scope: str) -> User | None:
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("scope", "user") != scope:
        return None

    try:
        user_id = int(payload["sub"])
        token_version = int(payload.get("ver", -1))
    except (KeyError, TypeError, ValueError):
        return None

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active or token_version != user.token_version:
        return None
    return user


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    user = await _resolve_user(db, credentials, scope="user")
    if user is None:
        raise HTTPException(401, "Unauthenticated.", headers={"WWW-Authenticate": "Bearer"})
    return user


async def get_current_user_optional(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User | None:
    return await _resolve_user(db, credentials, scope="user")


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]


async def get_current_admin(current_user: CurrentUser) -> User:
    if current_user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(403, "Administrator access required.")
    return current_user


async def get_current_super_admin(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    user = await _resolve_user(db, credentials, scope="admin")
    if user is None or user.role != "SUPER_ADMIN":
        raise HTTPException(403, "Super administrator access required.")
    return user


AdminUser = Annotated[User, Depends(get_current_admin)]
SuperAdminUser = Annotated[User, Depends(get_current_super_admin)]
