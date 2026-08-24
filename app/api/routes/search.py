# app/api/routes/search.py
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, OptionalUser
from app.models.models import Perception
from app.schemas.content import PerceptionOut
from app.services.perception_serialization import bulk_to_out

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[PerceptionOut])
async def search_perceptions(db: DbSession, viewer: OptionalUser, query: str = ""):
    if not query.strip():
        return []

    like = f"%{query.strip()}%"
    result = await db.execute(
        select(Perception)
        .where(Perception.body.ilike(like))
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
        .limit(30)
    )
    perceptions = result.scalars().all()
    return await bulk_to_out(db, list(perceptions), viewer.id if viewer else None)
