# app/api/routes/perceptions.py
import os
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Perception, Topic
from app.schemas.content import PerceptionOut
from app.services.perception_serialization import bulk_to_out, to_out
from app.services.storage import ALLOWED_MEDIA_TYPES, save_upload
from sqlalchemy import select
from sqlalchemy.orm import selectinload

settings = get_settings()


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
        .where(
            Perception.id == perception_id, Perception.user_id == current_user.id
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found"
        )

    if body is not None:
        perception.body = body

    if topic_id is not None:
        topic_exists = await db.execute(
            select(Topic.id).where(Topic.id == topic_id)
        )
        if topic_exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid topic_id",
            )
        perception.topic_id = topic_id

    # MEDIA REPLACEMENT & CLEANUP LOGIC
    if media is not None:
        # 1. Store a reference to the old media URL path before overwriting it
        old_media_url = perception.media_url

        # 2. Upload and save the brand new media file
        perception.media_url = await save_upload(
            media, "perceptions", allowed_types=ALLOWED_MEDIA_TYPES
        )

        # 3. Clean up the old asset from disk if it exists
        if old_media_url:
            try:
                # Extract relative folder location (e.g., from "/storage/perceptions/xyz.jpg" to "storage/perceptions/xyz.jpg")
                relative_path = old_media_url.lstrip("/")
                file_path = Path(settings.STORAGE_ROOT) / relative_path.replace(
                    settings.STORAGE_URL_PREFIX.lstrip("/"), ""
                ).lstrip("/")

                # Check if it physically exists on disk and is a file, then remove it
                if file_path.exists() and file_path.is_file():
                    os.remove(file_path)
            except Exception as e:
                # Log the error but don't crash the request—updating the DB record takes priority
                print(f"Failed to delete orphaned file {old_media_url}: {e}")

    await db.commit()
    
    # Refreshing native database properties (body, media_url, updated_at, etc.) safely without any keyword errors
    await db.refresh(perception)
    
    #Re-fetch the fully bound relationships to populate perception.user and perception.topic
    # This matches exactly what selectinload expects in an async environment
    result_refreshed = await db.execute(
        select(Perception)
        .where(Perception.id == perception.id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    perception = result_refreshed.scalar_one()

    # Serializing safely loaded object structure
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
