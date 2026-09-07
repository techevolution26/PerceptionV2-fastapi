# app/schemas/user.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    professional_industries: list[str] = Field(default_factory=list)
    professional_roles: list[str] = Field(default_factory=list)
    primary_professional_role: str | None = None
    primary_professional_role_label: str | None = None
    professional_role_labels: list[str] = Field(default_factory=list)
    verified_professional_roles: list[str] = Field(default_factory=list)
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
    verification_status: str = "NOT_APPLIED"
    verification_badge: str | None = None


class UserWithUnread(UserSlim):
    unread: int = 0
    lastMessage: datetime | None = None
    lastMessagePreview: str | None = None


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(c.isupper() for c in value) or not any(c.islower() for c in value) or not any(c.isdigit() for c in value) or not any(not c.isalnum() for c in value):
            raise ValueError("Password must contain uppercase, lowercase, number, and special character.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20, max_length=8192)


class AuthResponse(BaseModel):
    user: UserMe
    token: str
    is_new_user: bool = False


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
    professional_industries: list[str] | None = Field(default=None, max_length=20)
    professional_roles: list[str] | None = Field(default=None, max_length=20)
    primary_professional_role: str | None = Field(default=None, max_length=128)
