from typing import Literal

from pydantic import BaseModel, Field

DecisionIntent = Literal[
    "research",
    "business",
    "policy",
    "journalism",
    "education",
    "product",
    "professional",
    "general_exploration",
]


class DecisionObservation(BaseModel):
    title: str
    description: str
    evidence_source: str
    sample_size: int


class DecisionConsideration(BaseModel):
    title: str
    description: str


class InvestigationPath(BaseModel):
    title: str
    question: str
    rationale: str
    evidence_basis: str
    validation_step: str


class DecisionIntelligence(BaseModel):
    intent: DecisionIntent
    status: Literal["available", "insufficient_sample"]
    summary: str
    observations: list[DecisionObservation] = Field(default_factory=list)
    investigation_paths: list[InvestigationPath] = Field(default_factory=list)
    considerations: list[DecisionConsideration] = Field(default_factory=list)
    evidence_invariant: bool
    guardrail: str
    limitations: list[str] = Field(default_factory=list)
