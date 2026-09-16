from pydantic import BaseModel, Field

from app.schemas.content import PerceptionOut


class RelatedPerception(BaseModel):
    reason: str
    score: float = Field(ge=0)
    perception: PerceptionOut


class RelatedPerceptionsOut(BaseModel):
    source_perception_id: int
    items: list[RelatedPerception] = Field(default_factory=list)
