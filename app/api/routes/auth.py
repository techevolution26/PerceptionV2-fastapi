# app/api/routes/auth.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.user import AuthResponse, LoginRequest, RegisterRequest

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession):
    if payload.password != payload.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": {"password": ["The password confirmation does not match."]}},
        )
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": {"password": ["The password must be at least 8 characters."]}},
        )

    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": {"email": ["The email has already been taken."]}},
        )

    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(user=user, token=token)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: DbSession):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": {"email": ["The provided credentials are incorrect."]}},
        )

    token = create_access_token(user.id)
    return AuthResponse(user=user, token=token)


@router.post("/logout")
async def logout(_current_user: CurrentUser):
    # JWTs are stateless — nothing to revoke server-side without a denylist.
    # Kept as a route for frontend/API-contract parity with the old Sanctum
    # `POST /api/logout`. If you need real revocation later, add a Redis
    # denylist keyed by token jti with a TTL matching token expiry.
    return {"message": "Logged out"}
