# app/api/routes/likes.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.models import Like, Perception
from app.schemas.misc import LikeToggleOut

router = APIRouter(tags=["likes"])


async def _likes_count(db: DbSession, perception_id: int) -> int:
    return (
        await db.execute(select(func.count()).select_from(Like).where(Like.perception_id == perception_id))
    ).scalar_one()


@router.post("/perceptions/{perception_id}/like", response_model=LikeToggleOut)
async def like_perception(perception_id: int, current_user: CurrentUser, db: DbSession):
    exists = await db.execute(select(Perception.id).where(Perception.id == perception_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")

    existing = await db.execute(
        select(Like).where(Like.perception_id == perception_id, Like.user_id == current_user.id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(Like(perception_id=perception_id, user_id=current_user.id))
        await db.commit()

    return LikeToggleOut(liked=True, likes_count=await _likes_count(db, perception_id))


@router.delete("/perceptions/{perception_id}/like", response_model=LikeToggleOut)
async def unlike_perception(perception_id: int, current_user: CurrentUser, db: DbSession):
    existing = await db.execute(
        select(Like).where(Like.perception_id == perception_id, Like.user_id == current_user.id)
    )
    like = existing.scalar_one_or_none()
    if like is not None:
        await db.delete(like)
        await db.commit()

    return LikeToggleOut(liked=False, likes_count=await _likes_count(db, perception_id))
