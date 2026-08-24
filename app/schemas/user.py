# app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    """Public profile shape — NEVER includes email. The original Laravel
    endpoint leaked email on the public `/users/{id}` route; intentionally
    excluded here."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bio: str | None = None
    avatar_url: str | None = None
    profession: str | None = None
    created_at: datetime


class UserProfile(UserPublic):
    """Public profile + engagement counts, used by ProfileSection.jsx."""

    perceptions_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    topics_count: int = 0


class UserMe(UserPublic):
    """Only ever returned to the authenticated user themself — includes email."""

    email: EmailStr


class UserSlim(BaseModel):
    """Minimal embed used inside perceptions/comments."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None = None
    profession: str | None = None


class UserWithUnread(UserSlim):
    unread: int = 0
    lastMessage: datetime | None = None
    lastMessagePreview: str | None = None


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    password_confirmation: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user: UserMe
    token: str


class UpdateMeRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
