from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import jwt
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)

def create_access_token(subject: int, expires_minutes: int | None = None, *, scope: str = "user", token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {
            "sub": str(subject),
            "exp": exp,
            "iat": now,
            "jti": uuid.uuid4().hex,
            "scope": scope,
            "ver": token_version,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["sub", "exp", "iat", "jti", "scope", "ver", "iss", "aud"]},
        )
        int(payload["sub"])
        if payload.get("scope") not in {"user", "admin"}:
            return None
        return payload
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
