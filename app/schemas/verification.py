from datetime import datetime
from pydantic import BaseModel, Field


class VerificationApplicationCreate(BaseModel):
    profession: str = Field(min_length=2, max_length=255)
    focus: str = Field(min_length=2, max_length=255)
    primary_topic_id: int | None = None
    requested_topic_ids: list[int] = Field(default_factory=list, max_length=50)
    evidence: str | None = Field(default=None, max_length=5000)


class VerificationApplicationOut(BaseModel):
    id: int
    profession: str
    focus: str
    primary_topic_id: int | None
    requested_topic_ids: list[int]
    evidence: str | None
    status: str
    badge: str | None
    reviewer_note: str | None
    created_at: datetime
    updated_at: datetime
