# app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    """Minimal public identity. Account and analytics-profile fields stay private."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bio: str | None = None
    avatar_url: str | None = None
    profession: str | None = None
    verification_status: str = "NOT_APPLIED"
    verification_badge: str | None = None
    created_at: datetime


class UserProfile(UserPublic):
    """Public profile + engagement counts; never exposes account credentials."""
    perceptions_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    topics_count: int = 0
    is_following: bool = False
    can_message: bool = False


class UserMe(UserPublic):
    """Authenticated account shape; private profile and analytics fields live here."""

    email: EmailStr
    role: str = "USER"
    professional_focus: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    analytics_specialties: list[int] = Field(default_factory=list)
    primary_analytics_topic_id: int | None = None


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

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20, max_length=8192)


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
