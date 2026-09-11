from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.perception_intelligence import SemanticDistribution, SemanticTheme


class TopicIntelligenceContext(BaseModel):
    schema_version: str
    topic_id: int
    topic_name: str
    period_start: datetime
    period_end: datetime
    period_days: int
    scope: Literal["topic_intelligence"]
    viewer_lens: Literal["observer"]
    access_tier: Literal["full", "free_teaser"]
    upgrade_available: bool
    upgrade_message: str | None


class TopicMeasurement(BaseModel):
    value: int | float | None
    available: bool
    description: str


class TopicMeasurements(BaseModel):
    perceptions: TopicMeasurement
    qualifying_perceptions: TopicMeasurement
    analyzed_comments: TopicMeasurement
    unique_participants: TopicMeasurement


class TopicPerceptionSegment(BaseModel):
    perception_id: int
    sample_size: int
    topic_name: str


class TopicSemantic(BaseModel):
    status: Literal["insufficient_sample", "insufficient_breadth", "available"]
    note: str
    sample_minimum: int
    perception_minimum: int
    analyzed_comment_count: int
    qualifying_perception_count: int
    quality_score: float | None
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    concern_themes: list[SemanticTheme]
    agreement_themes: list[SemanticTheme]
    disagreement_themes: list[SemanticTheme]


class TopicPerspective(BaseModel):
    label: str
    sample_size: int
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class TopicPerspectives(BaseModel):
    status: Literal["available", "insufficient_sample", "insufficient_segments"]
    sample_minimum: int
    analyzed_comment_count: int
    professional: list[dict] = Field(default_factory=list)
    geographic: list[dict] = Field(default_factory=list)
    professional_geographic: list[dict] = Field(default_factory=list)
    note: str


class TopicTemporalBucket(BaseModel):
    period_start: datetime
    period_end: datetime
    sample_size: int
    status: Literal["available", "insufficient_sample"]
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class TopicTemporal(BaseModel):
    bucket_days: int
    qualifying_bucket_count: int
    buckets: list[TopicTemporalBucket]
    status: Literal["available", "insufficient_sample"]
    note: str


class TopicPattern(BaseModel):
    label: str
    description: str
    sample_size: int
    evidence_type: str
    limitations: list[str] = Field(default_factory=list)


class TopicIntelligenceProvenance(BaseModel):
    trace_id: str
    evidence_chain: list[str] = Field(default_factory=list)
    source: Literal["topic_intelligence"]
    evidence_types: list[str] = Field(default_factory=list)
    sample_size: int
    period_start: datetime
    period_end: datetime
    scope: Literal["topic_intelligence"]
    viewer_lens: Literal["observer"]
    quality_score: float | None = None
    qualification: str
    limitations: list[str] = Field(default_factory=list)


class TopicDecisionContext(BaseModel):
    intent: str
    status: Literal["available", "insufficient_sample"]
    summary: str
    evidence_invariant: str
    guardrail: str
    limitations: list[str] = Field(default_factory=list)


class TopicIntelligence(BaseModel):
    schema_version: str
    context: TopicIntelligenceContext
    measurements: TopicMeasurements
    perceptions: list[TopicPerceptionSegment]
    semantic: TopicSemantic
    perspectives: TopicPerspectives
    temporal: TopicTemporal
    patterns: list[TopicPattern]
    decision_context: TopicDecisionContext
    provenance: TopicIntelligenceProvenance
    limitations: list[str]
