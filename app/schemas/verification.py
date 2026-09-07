from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VerificationApplicationCreate(BaseModel):
    profession: str = Field(min_length=2, max_length=255)
    focus: str = Field(min_length=2, max_length=255)
    industry_codes: list[str] = Field(default_factory=list, max_length=20)
    professional_role_codes: list[str] = Field(default_factory=list, max_length=20)
    primary_professional_role: str | None = Field(default=None, max_length=128)
    primary_topic_id: int | None = None
    requested_topic_ids: list[int] = Field(default_factory=list, max_length=50)
    evidence: str | None = Field(default=None, max_length=5000)


class VerificationApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profession: str
    focus: str
    primary_topic_id: int | None
    requested_topic_ids: list[int]
    evidence: str | None
    status: str
    badge: str | None
    industry_codes: list[str] = Field(default_factory=list)
    professional_role_codes: list[str] = Field(default_factory=list)
    primary_professional_role: str | None = None
    reviewer_note: str | None
    created_at: datetime
    updated_at: datetime
