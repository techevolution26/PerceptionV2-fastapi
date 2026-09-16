from pydantic import BaseModel, Field

from app.schemas.content import PerceptionOut, TopicOut
from app.schemas.user import UserSlim


class RecommendationItem(BaseModel):
    """An explainable recommendation without exposing ranking internals."""

    type: str
    reason: str
    score: float = Field(ge=0)


class TopicRecommendation(RecommendationItem):
    type: str = "topic"
    topic: TopicOut


class CreatorRecommendation(RecommendationItem):
    type: str = "creator"
    creator: UserSlim


class PerceptionRecommendation(RecommendationItem):
    type: str = "perception"
    perception: PerceptionOut


class RecommendationsOut(BaseModel):
    topics: list[TopicRecommendation] = Field(default_factory=list)
    creators: list[CreatorRecommendation] = Field(default_factory=list)
    perceptions: list[PerceptionRecommendation] = Field(default_factory=list)
