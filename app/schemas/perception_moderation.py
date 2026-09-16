from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PerceptionModerationStatus(str, Enum):
    PUBLISHED = "published"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REMOVED = "removed"


class PerceptionModerationDecision(BaseModel):
    status: PerceptionModerationStatus
    review_note: str | None = Field(default=None, max_length=2000)


class PerceptionPendingReviewOut(BaseModel):
    perception_id: int
    status: PerceptionModerationStatus = PerceptionModerationStatus.PENDING_REVIEW
    message: str


class PerceptionModerationQueueItem(BaseModel):
    perception_id: int
    body: str
    topic_id: int | None
    topic_name: str | None
    author_id: int
    author_name: str
    status: PerceptionModerationStatus
    risk_level: str
    flags: list[str] = Field(default_factory=list)
    checked_at: datetime
    created_at: datetime
