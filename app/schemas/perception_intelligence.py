from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IntelligenceAuthor(BaseModel):
    professional_role: str | None
    verified: bool


class IntelligenceContext(BaseModel):
    schema_version: str
    topic_id: int | None
    topic_name: str | None
    perception_id: int
    period_start: datetime
    period_end: datetime
    period_days: int
    scope: Literal["creator_analytics", "conversation_intelligence"]
    viewer_lens: Literal["author", "observer"]
    author: IntelligenceAuthor


class IntelligenceMeasurement(BaseModel):
    value: int | float | None
    available: bool
    description: str


class IntelligenceMeasurements(BaseModel):
    likes: IntelligenceMeasurement
    comments: IntelligenceMeasurement
    views: IntelligenceMeasurement
    shares: IntelligenceMeasurement
    engagement_rate: IntelligenceMeasurement
    daily_activity: list[dict]


class AudienceBreakdown(BaseModel):
    minimum: int
    available: bool
    countries: list[dict]
    regions: list[dict]
    professional_roles: list[dict]
    verified_professional_roles: list[dict]


class IntelligenceAudience(BaseModel):
    unique_participants: int
    breakdown: AudienceBreakdown


class SemanticDistribution(BaseModel):
    label: str
    comments: int
    share: float


class SemanticTheme(BaseModel):
    theme: str
    comments: int
    share: float


class SemanticIntelligence(BaseModel):
    status: Literal["insufficient_sample", "available"]
    note: str
    sample_minimum: int
    analyzed_comment_count: int
    period_days: int
    quality_score: float | None
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    concern_themes: list[SemanticTheme]
    agreement_themes: list[SemanticTheme]
    disagreement_themes: list[SemanticTheme]


class ProfessionalPerspective(BaseModel):
    role_code: str
    role_label: str
    sample_size: int
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class GeographicPerspective(BaseModel):
    geography: str
    sample_size: int
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class CrossLensPerspective(ProfessionalPerspective):
    geography: str


class IntelligencePerspectives(BaseModel):
    status: Literal["insufficient_sample", "available", "insufficient_segments"]
    note: str
    sample_minimum: int
    analyzed_comment_count: int
    professional: list[ProfessionalPerspective]
    geographic: list[GeographicPerspective]
    cross_lens: list[CrossLensPerspective]


class IntelligenceEvidence(BaseModel):
    type: str
    observed: list[dict] | dict | int | float | None


class IntelligencePattern(BaseModel):
    label: str
    description: str
    evidence_types: list[str] = Field(default_factory=list)


class IntelligenceSignal(BaseModel):
    label: str
    description: str
    status: Literal["observed_signal"]
    sample_size: int
    limitations: list[str] = Field(default_factory=list)


class DecisionContext(BaseModel):
    intent: Literal[
        "research",
        "business",
        "policy",
        "journalism",
        "education",
        "product",
        "professional",
        "general_exploration",
    ]
    signals: list[IntelligenceSignal]
    evidence_invariant: bool
    guardrail: str


class IntelligenceMethodology(BaseModel):
    sample_minimum: int
    quality_score_definition: str
    limitations: list[str]
    rules: list[str]


class PerceptionIntelligence(BaseModel):
    context: IntelligenceContext
    measurements: IntelligenceMeasurements
    audience: IntelligenceAudience
    semantic: SemanticIntelligence
    perspectives: IntelligencePerspectives
    patterns: list[IntelligencePattern]
    signals: list[IntelligenceSignal]
    decision_context: DecisionContext
    methodology: IntelligenceMethodology
