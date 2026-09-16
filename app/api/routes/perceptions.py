# app/api/routes/perceptions.py
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Perception, PerceptionModeration, Topic, User
from app.schemas.content import PerceptionOut
from app.schemas.perception_moderation import PerceptionPendingReviewOut
from app.schemas.related_perceptions import RelatedPerceptionsOut
from app.services.perception_serialization import bulk_to_out, to_out
from app.services.storage import ALLOWED_MEDIA_TYPES, save_upload
from app.services.personalization import get_personalized_perceptions
from app.services.related_perceptions import get_related_perceptions
from app.services.perception_moderation import assess_perception
from app.services.rate_limiter import enforce_rate_limit
from sqlalchemy import select
from sqlalchemy.orm import selectinload

settings = get_settings()


router = APIRouter(tags=["perceptions"])


@router.get("/perceptions", response_model=list[PerceptionOut])
async def list_perceptions(db: DbSession, viewer: OptionalUser, topic_id: int | None = None):
    query = (
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
    )
    if topic_id is not None:
        query = query.where(Perception.topic_id == topic_id)

    result = await db.execute(query)
    perceptions = result.scalars().all()
    return await bulk_to_out(db, list(perceptions), viewer.id if viewer else None)


@router.get("/perceptions/personalized", response_model=list[PerceptionOut])
async def personalized_perceptions(
    current_user: CurrentUser,
    db: DbSession,
):
    perceptions = await get_personalized_perceptions(db, current_user)
    return await bulk_to_out(db, perceptions, current_user.id)


@router.post("/perceptions", response_model=PerceptionOut | PerceptionPendingReviewOut, status_code=status.HTTP_201_CREATED)
async def create_perception(
    current_user: CurrentUser,
    db: DbSession,
    body: str = Form(...),
    topic_id: int = Form(...),
    media: UploadFile | None = File(default=None),
):
    await enforce_rate_limit(
        scope="perception-create-minute",
        identity=f"user:{current_user.id}",
        limit=settings.PERCEPTION_CREATE_RATE_LIMIT_PER_MINUTE,
        message="You are posting perceptions too quickly. Please take a moment before adding another.",
    )

    normalized_body = " ".join(body.split())
    if not normalized_body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A perception needs some text before it can enter a conversation.",
        )
    if len(normalized_body) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A perception cannot exceed 2000 characters.",
        )

    topic_exists = await db.execute(select(Topic.id).where(Topic.id == topic_id))
    if topic_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid topic_id")

    media_url = None
    if media is not None:
        media_url = await save_upload(media, "perceptions", allowed_types=ALLOWED_MEDIA_TYPES)

    perception = Perception(user_id=current_user.id, topic_id=topic_id, body=normalized_body, media_url=media_url)
    db.add(perception)
    await db.flush()

    assessment = assess_perception(perception.body)
    db.add(
        PerceptionModeration(
            perception_id=perception.id,
            status=assessment.status,
            risk_level=assessment.risk_level,
            flags=assessment.flags,
        )
    )
    await db.commit()

    if assessment.status == "pending_review":
        return PerceptionPendingReviewOut(
            perception_id=perception.id,
            message="Your perception was received and sent for a quick review before it appears publicly.",
        )

    await db.refresh(perception, attribute_names=["user", "topic"])
    return await to_out(db, perception, current_user.id)


@router.get("/perceptions/{perception_id}/related", response_model=RelatedPerceptionsOut)
async def related_perceptions(
    perception_id: int,
    db: DbSession,
    viewer: OptionalUser,
):
    result = await get_related_perceptions(db, perception_id, viewer.id if viewer else None)
    if not result.items:
        source = await db.scalar(select(Perception.id).where(Perception.id == perception_id))
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")
    return result


@router.get("/perceptions/{perception_id}", response_model=PerceptionOut)
async def get_perception(perception_id: int, db: DbSession, viewer: OptionalUser):
    result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.id == perception_id,
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
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
        .join(User, User.id == Perception.user_id)
        .outerjoin(PerceptionModeration, PerceptionModeration.perception_id == Perception.id)
        .where(
            Perception.topic_id == topic_id,
            User.is_active.is_(True),
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
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

    moderation = await db.scalar(
        select(PerceptionModeration).where(PerceptionModeration.perception_id == perception.id)
    )
    assessment = assess_perception(perception.body)
    if moderation is None:
        moderation = PerceptionModeration(perception_id=perception.id)
        db.add(moderation)
    moderation.status = assessment.status
    moderation.risk_level = assessment.risk_level
    moderation.flags = assessment.flags
    moderation.checked_at = datetime.now(timezone.utc)
    moderation.reviewed_by_user_id = None
    moderation.reviewed_at = None
    moderation.review_note = None

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
