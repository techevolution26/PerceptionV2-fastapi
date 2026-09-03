# app/api/deps.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User

DbSession = Annotated[AsyncSession, Depends(get_db)]

# auto_error=False so we can support both "required auth" and "optional auth"
# endpoints (many profile/topic/perception reads are public, but personalize
# the response — e.g. liked_by_user — when a valid token IS present).
_bearer = HTTPBearer(auto_error=False)


async def _resolve_user(
    db: AsyncSession, credentials: HTTPAuthorizationCredentials | None
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    user = await _resolve_user(db, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User | None:
    return await _resolve_user(db, credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUser) -> User:
    if current_user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return current_user


AdminUser = Annotated[User, Depends(get_current_admin)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
