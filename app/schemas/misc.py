# app/schemas/misc.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    data: dict
    read_at: datetime | None = None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: int
    to_user_id: int
    body: str
    read_at: datetime | None = None
    created_at: datetime
    edited_at: datetime | None = None
    deleted_at: datetime | None = None


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class EditMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class ConversationActionOut(BaseModel):
    archived: bool = False
    deleted: bool = False


class LikeToggleOut(BaseModel):
    liked: bool
    likes_count: int


class FollowToggleOut(BaseModel):
    followed: bool | None = None
    message: str | None = None


class NotificationsListOut(BaseModel):
    """Wrapper for GET /notifications — matches what NotificationsPanel.jsx
    expects (`payload.data`), and gives openapi-typescript something to
    generate a real schema from instead of an untyped dict."""

    data: list[NotificationOut]


class EditMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class ConversationActionOut(BaseModel):
    archived: bool = False
    deleted: bool = False


class UnreadCountOut(BaseModel):
    unread_count: int = Field(ge=0)
