from typing import Literal

from pydantic import BaseModel, Field


class ComparativePerception(BaseModel):
    perception_id: int
    title: str
    topic_name: str | None
    sample_size: int
    status: Literal["available", "insufficient_sample"]
    leading_stance: str | None
    leading_theme: str | None
    stance_distribution: list[dict]
    top_themes: list[dict]


class ComparativeComparison(BaseModel):
    perception_a_id: int
    perception_a_title: str
    perception_b_id: int
    perception_b_title: str
    sample_size_a: int
    sample_size_b: int
    leading_stance_a: str | None
    leading_stance_b: str | None
    shared_themes: list[str] = Field(default_factory=list)
    type: Literal["aligned", "stance_difference", "theme_difference", "mixed"]
    description: str


class ComparativeIntelligence(BaseModel):
    schema_version: str
    intent: Literal[
        "research", "business", "policy", "journalism", "education",
        "product", "professional", "general_exploration",
    ]
    status: Literal["available", "insufficient_sample"]
    sample_minimum: int
    perceptions: list[ComparativePerception]
    comparisons: list[ComparativeComparison]
    observations: list[dict]
    limitations: list[str]
    decision_note: str
