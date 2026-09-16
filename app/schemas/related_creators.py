from pydantic import BaseModel, Field

from app.schemas.user import UserProfile


class RelatedCreator(BaseModel):
    reason: str
    score: float = Field(ge=0)
    creator: UserProfile


class RelatedCreatorsOut(BaseModel):
    source_topic_id: int
    items: list[RelatedCreator] = Field(default_factory=list)
