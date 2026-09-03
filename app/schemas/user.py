# app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    professional_focus: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    analytics_specialties: list[int] = Field(default_factory=list)
    primary_analytics_topic_id: int | None = None
    verification_status: str = "NOT_APPLIED"
    verification_badge: str | None = None
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
    role: str = "USER"


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
    profession: str | None = None
    professional_focus: str | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    region: str | None = None
    city: str | None = None
    primary_analytics_topic_id: int | None = None
    analytics_specialties: list[int] | None = None
