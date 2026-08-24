# app/api/routes/perceptions.py
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Perception, Topic
from app.schemas.content import PerceptionOut
from app.services.perception_serialization import bulk_to_out, to_out
from app.services.storage import ALLOWED_MEDIA_TYPES, save_upload

router = APIRouter(tags=["perceptions"])


@router.get("/perceptions", response_model=list[PerceptionOut])
async def list_perceptions(db: DbSession, viewer: OptionalUser, topic_id: int | None = None):
    query = (
        select(Perception)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
    )
    if topic_id is not None:
        query = query.where(Perception.topic_id == topic_id)

    result = await db.execute(query)
    perceptions = result.scalars().all()
    return await bulk_to_out(db, list(perceptions), viewer.id if viewer else None)


@router.post("/perceptions", response_model=PerceptionOut, status_code=status.HTTP_201_CREATED)
async def create_perception(
    current_user: CurrentUser,
    db: DbSession,
    body: str = Form(...),
    topic_id: int = Form(...),
    media: UploadFile | None = File(default=None),
):
    topic_exists = await db.execute(select(Topic.id).where(Topic.id == topic_id))
    if topic_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid topic_id")

    media_url = None
    if media is not None:
        media_url = await save_upload(media, "perceptions", allowed_types=ALLOWED_MEDIA_TYPES)

    perception = Perception(user_id=current_user.id, topic_id=topic_id, body=body, media_url=media_url)
    db.add(perception)
    await db.commit()
    await db.refresh(perception, attribute_names=["user", "topic"])

    return await to_out(db, perception, current_user.id)


@router.get("/perceptions/{perception_id}", response_model=PerceptionOut)
async def get_perception(perception_id: int, db: DbSession, viewer: OptionalUser):
    result = await db.execute(
        select(Perception)
        .where(Perception.id == perception_id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")

    return await to_out(db, perception, viewer.id if viewer else None)


@router.get("/topics/{topic_id}/perceptions", response_model=list[PerceptionOut])
async def perceptions_by_topic(topic_id: int, db: DbSession, viewer: OptionalUser):
    result = await db.execute(
        select(Perception)
        .where(Perception.topic_id == topic_id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
    )
    perceptions = result.scalars().all()
    return await bulk_to_out(db, list(perceptions), viewer.id if viewer else None)


@router.put("/perceptions/{perception_id}", response_model=PerceptionOut)
async def update_perception(
    perception_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: str | None = Form(default=None),
    topic_id: int | None = Form(default=None),
    media: UploadFile | None = File(default=None),
):
    result = await db.execute(
        select(Perception)
        .where(Perception.id == perception_id, Perception.user_id == current_user.id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")

    if body is not None:
        perception.body = body
    if topic_id is not None:
        topic_exists = await db.execute(select(Topic.id).where(Topic.id == topic_id))
        if topic_exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid topic_id")
        perception.topic_id = topic_id
    if media is not None:
        perception.media_url = await save_upload(media, "perceptions", allowed_types=ALLOWED_MEDIA_TYPES)

    await db.commit()
    await db.refresh(perception, attribute_names=["user", "topic"])
    return await to_out(db, perception, current_user.id)


@router.delete("/perceptions/{perception_id}")
async def delete_perception(perception_id: int, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Perception).where(Perception.id == perception_id, Perception.user_id == current_user.id)
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")

    await db.delete(perception)
    await db.commit()
    return {"message": "Deleted"}
