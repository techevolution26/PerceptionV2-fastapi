from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InvestigationThreadStatus = Literal["open", "in_progress", "verified", "dismissed"]


class InvestigationThreadCreate(BaseModel):
    perception_id: int
    title: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(min_length=1, max_length=2000)
    evidence_basis: str = Field(min_length=1, max_length=1000)
    validation_step: str = Field(min_length=1, max_length=2000)
    evidence_trace_id: str | None = Field(default=None, max_length=128)


class InvestigationThreadUpdate(BaseModel):
    status: InvestigationThreadStatus | None = None
    note: str | None = Field(default=None, max_length=4000)


class InvestigationThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    perception_id: int
    title: str
    question: str
    rationale: str
    evidence_basis: str
    validation_step: str
    evidence_trace_id: str | None
    status: InvestigationThreadStatus
    note: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationThreadListOut(BaseModel):
    items: list[InvestigationThreadOut]
