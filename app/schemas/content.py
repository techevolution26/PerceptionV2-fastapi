# app/schemas/content.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserSlim


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    image_url: str | None = None


class TopicSlim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TopicsListOut(BaseModel):
    """Wrapper for GET /topics — matches what the Next.js BFF proxy already
    expects (`data.topics`) and what /topics/route.js already unwraps."""

    topics: list[TopicOut]


class PerceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    media_url: str | None = None
    created_at: datetime
    updated_at: datetime
    user: UserSlim
    topic: TopicSlim | None = None
    likes_count: int = 0
    comments_count: int = 0
    liked_by_user: bool = False


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    perception_id: int
    parent_comment_id: int | None = None
    body: str | None = None
    media_url: str | None = None
    created_at: datetime
    user: UserSlim
    replies: list["CommentOut"] = []


CommentOut.model_rebuild()
