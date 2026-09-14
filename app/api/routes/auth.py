import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import delete, select
from redis.asyncio import Redis
from datetime import datetime, timedelta, timezone
import secrets

import hashlib
from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.services.email import send_password_reset_email
from app.models.models import PasswordResetToken, User
from app.schemas.user import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)

router = APIRouter(tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)


async def _rate_limit(request: Request, *, bucket: str = "login", identity: str | None = None, limit: int | None = None):
    """Redis-backed fixed-window limiter. In production, Redis failure fails closed."""
    key_identity = identity or (request.client.host if request.client else "unknown")
    digest = hashlib.sha256(key_identity.strip().lower().encode()).hexdigest()
    key = f"auth:{bucket}:{digest}"
    try:
        async with Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
    except Exception as exc:
        logger.warning(
            "Authentication rate-limit dependency unavailable: %s",
            type(exc).__name__,
            extra={"bucket": bucket, "redis_url_configured": bool(settings.REDIS_URL)},
        )
        if settings.RATE_LIMIT_FAIL_OPEN:
            return
        raise HTTPException(503, "Authentication service temporarily unavailable.")
    if count > (limit or settings.LOGIN_RATE_LIMIT_PER_MINUTE):
        raise HTTPException(429, "Too many authentication attempts. Try again shortly.")


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: DbSession):
    await _rate_limit(request, bucket="register", identity=f"ip:{request.client.host if request.client else 'unknown'}", limit=5)
    if payload.password != payload.password_confirmation:
        raise HTTPException(
            422, {"errors": {"password": ["The password confirmation does not match."]}}
        )
    if len(payload.password) < 8:
        raise HTTPException(
            422,
            {"errors": {"password": ["The password must be at least 8 characters."]}},
        )
    if await db.scalar(select(User.id).where(User.email == str(payload.email).lower().strip())):
        raise HTTPException(
            422, {"errors": {"email": ["The email has already been taken."]}}
        )
    user = User(
        name=payload.name.strip(),
        email=str(payload.email).lower().strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(
        user=user,
        token=create_access_token(user.id, token_version=user.token_version),
        is_new_user=True,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession):
    normalized_email = str(payload.email).lower().strip()
    await _rate_limit(request, identity=f"ip:{request.client.host if request.client else 'unknown'}")
    await _rate_limit(request, bucket="login-account", identity=normalized_email)
    user = await db.scalar(select(User).where(User.email == normalized_email))
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            422, {"errors": {"email": ["The provided credentials are incorrect."]}}
        )
    if not user.is_active:
        raise HTTPException(403, "This account is suspended.")
    return AuthResponse(
        user=user,
        token=create_access_token(user.id, token_version=user.token_version),
        is_new_user=False,
    )


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleLoginRequest, request: Request, db: DbSession):
    await _rate_limit(request)
    ids = {x.strip() for x in settings.GOOGLE_CLIENT_IDS.split(",") if x.strip()}
    if not ids:
        raise HTTPException(503, "Google sign-in is not configured.")
    try:
        claims = id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), clock_skew_in_seconds=10
        )
    except ValueError:
        raise HTTPException(401, "Invalid Google identity token.")
    if claims.get("aud") not in ids or claims.get("iss") not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise HTTPException(401, "Google identity could not be verified.")
    sub = str(claims.get("sub", ""))
    email = str(claims.get("email", "")).lower().strip()
    if not sub or not email or claims.get("email_verified") is not True:
        raise HTTPException(401, "A verified Google account is required.")
    user = await db.scalar(
        select(User).where((User.google_sub == sub) | (User.email == email))
    )
    is_new_user = user is None
    if user is None:
        user = User(
            name=str(claims.get("name") or email.split("@")[0])[:255],
            email=email,
            password_hash=hash_password(__import__("secrets").token_urlsafe(32)),
            google_sub=sub,
            avatar_url=claims.get("picture"),
        )
        db.add(user)
    else:
        if not user.is_active:
            raise HTTPException(403, "This account is suspended.")
        if user.google_sub and user.google_sub != sub:
            raise HTTPException(409, "This email is linked to another Google identity.")
        user.google_sub = sub
        if not user.avatar_url and claims.get("picture"):
            user.avatar_url = str(claims["picture"])
    await db.commit()
    await db.refresh(user)
    return AuthResponse(
        user=user,
        token=create_access_token(user.id, token_version=user.token_version),
        is_new_user=is_new_user,
    )


@router.post("/logout")
async def logout(current_user: CurrentUser, db: DbSession):
    current_user.token_version += 1
    await db.commit()
    return {"message": "Logged out"}


@router.post("/admin/session", response_model=dict)
async def admin_session(
    payload: LoginRequest, request: Request, current_user: CurrentUser, db: DbSession
):
    await _rate_limit(request, bucket="admin-session", identity=f"user:{current_user.id}", limit=settings.ADMIN_SESSION_RATE_LIMIT_PER_MINUTE)
    if (
        current_user.role != "SUPER_ADMIN"
        or payload.email.lower() != current_user.email.lower()
        or current_user.password_hash is None
        or not verify_password(payload.password, current_user.password_hash)
    ):
        raise HTTPException(403, "Admin console authorization failed.")
    return {
        "token": create_access_token(
            current_user.id,
            expires_minutes=settings.ADMIN_SESSION_EXPIRE_MINUTES,
            scope="admin",
            token_version=current_user.token_version,
        ),
        "expires_in": settings.ADMIN_SESSION_EXPIRE_MINUTES * 60,
    }


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    """Start recovery without revealing whether an email is registered."""
    normalized_email = str(payload.email).lower().strip()
    await _rate_limit(
        request,
        bucket="password-reset-ip",
        identity=f"ip:{request.client.host if request.client else 'unknown'}",
        limit=settings.PASSWORD_RESET_RATE_LIMIT_PER_MINUTE,
    )
    await _rate_limit(
        request,
        bucket="password-reset-account",
        identity=normalized_email,
        limit=settings.PASSWORD_RESET_RATE_LIMIT_PER_MINUTE,
    )

    user = await db.scalar(select(User).where(User.email == normalized_email, User.is_active.is_(True)))
    # Keep the response identical whether the account exists or not.
    if user is not None:
        await db.execute(
            delete(PasswordResetToken).where(
                (PasswordResetToken.user_id == user.id)
                | (PasswordResetToken.expires_at < datetime.now(timezone.utc))
            )
        )
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            requested_ip=request.client.host if request.client else None,
        )
        db.add(reset_token)
        await db.commit()
        reset_url = f"{settings.PASSWORD_RESET_URL}?token={raw_token}"
        background_tasks.add_task(
            send_password_reset_email,
            recipient=user.email,
            reset_url=reset_url,
        )
    else:
        await db.rollback()

    return {"message": "If an account exists for that email, password-reset instructions have been sent."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: DbSession):
    if payload.password != payload.password_confirmation:
        raise HTTPException(422, {"errors": {"password": ["The password confirmation does not match."]}})

    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    token = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        ).with_for_update()
    )
    if token is None:
        raise HTTPException(400, "This password-reset link is invalid or has expired.")

    user = await db.scalar(select(User).where(User.id == token.user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(400, "This password-reset link is invalid or has expired.")

    user.password_hash = hash_password(payload.password)
    user.token_version += 1
    token.used_at = now
    # One successful reset invalidates every other outstanding reset link.
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != token.id,
        )
    )
    await db.commit()
    return {"message": "Your password has been reset. Please sign in again."}


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: DbSession):
    if current_user.password_hash is None:
        raise HTTPException(409, "This account does not have a password yet. Use password recovery to set one.")
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(422, {"errors": {"current_password": ["The current password is incorrect."]}})
    if payload.password != payload.password_confirmation:
        raise HTTPException(422, {"errors": {"password": ["The password confirmation does not match."]}})
    if verify_password(payload.password, current_user.password_hash):
        raise HTTPException(422, {"errors": {"password": ["Choose a different password."]}})

    current_user.password_hash = hash_password(payload.password)
    current_user.token_version += 1
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == current_user.id))
    await db.commit()
    return {"message": "Your password has been changed. Please sign in again."}
