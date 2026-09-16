from pydantic import BaseModel, Field


class InvestigationPath(BaseModel):
    title: str
    question: str
    rationale: str
    evidence_basis: str
    validation_step: str


class InvestigationPaths(BaseModel):
    status: str
    paths: list[InvestigationPath] = Field(default_factory=list)
    note: str
