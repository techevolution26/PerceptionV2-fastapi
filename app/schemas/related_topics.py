from pydantic import BaseModel, Field

from app.schemas.content import TopicOut


class RelatedTopic(BaseModel):
    """An explainable topic relationship without exposing contributor identity."""

    reason: str
    score: float = Field(ge=0)
    topic: TopicOut


class RelatedTopicsOut(BaseModel):
    source_topic_id: int
    items: list[RelatedTopic] = Field(default_factory=list)
