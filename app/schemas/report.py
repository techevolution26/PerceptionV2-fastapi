from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PerceptionReportReason(str, Enum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    HATE = "hate"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    MISINFORMATION = "misinformation"
    IMPERSONATION = "impersonation"
    PRIVACY = "privacy"
    OTHER = "other"


class PerceptionReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class CreatePerceptionReportRequest(BaseModel):
    reason: PerceptionReportReason
    details: str | None = Field(default=None, max_length=2000)


class PerceptionReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    perception_id: int
    reason: PerceptionReportReason
    details: str | None
    status: PerceptionReportStatus
    created_at: datetime
    reviewed_at: datetime | None
    resolution_note: str | None


class UpdatePerceptionReportRequest(BaseModel):
    status: PerceptionReportStatus
    resolution_note: str | None = Field(default=None, max_length=2000)
