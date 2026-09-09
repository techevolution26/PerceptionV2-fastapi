from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.perception_intelligence import SemanticDistribution, SemanticTheme


class ProfileTheme(BaseModel):
    theme: str
    comment_count: int
    topic_count: int
    topics: list[str]


class ProfileTopic(BaseModel):
    topic_id: int | None
    topic_name: str
    perception_count: int
    sample_size: int
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class ProfileTemporalBucket(BaseModel):
    period_start: datetime
    period_end: datetime
    sample_size: int
    status: Literal["available", "insufficient_sample"]
    sentiment_distribution: list[SemanticDistribution]
    stance_distribution: list[SemanticDistribution]
    top_themes: list[SemanticTheme]
    question_count: int
    quality_score: float | None


class ProfileTemporal(BaseModel):
    bucket_days: int
    qualifying_bucket_count: int
    buckets: list[ProfileTemporalBucket]
    status: Literal["available", "insufficient_sample"]
    note: str


class ProfilePattern(BaseModel):
    label: str
    description: str
    sample_size: int
    limitations: list[str] = Field(default_factory=list)


class ProfileIntelligence(BaseModel):
    schema_version: str
    period_start: datetime
    period_end: datetime
    period_days: int
    sample_minimum: int
    perception_count: int
    topic_count: int
    analyzed_comment_count: int
    qualifying_perception_count: int
    topics: list[ProfileTopic]
    recurring_themes: list[ProfileTheme]
    temporal: ProfileTemporal
    patterns: list[ProfilePattern]
    limitations: list[str]
