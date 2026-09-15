from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.models import Perception, SavedPerception, User
from app.schemas.content import PerceptionOut
from app.schemas.misc import SaveToggleOut
from app.services.perception_serialization import bulk_to_out, to_out

router = APIRouter(tags=["saved perceptions"])


async def _get_active_perception(
    perception_id: int, db: DbSession
) -> Perception:
    result = await db.execute(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .where(
            Perception.id == perception_id,
            User.is_active.is_(True),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found"
        )
    return perception


@router.post(
    "/perceptions/{perception_id}/save",
    response_model=SaveToggleOut,
    status_code=status.HTTP_201_CREATED,
)
async def save_perception(
    perception_id: int, current_user: CurrentUser, db: DbSession
):
    await _get_active_perception(perception_id, db)

    existing = await db.execute(
        select(SavedPerception).where(
            SavedPerception.user_id == current_user.id,
            SavedPerception.perception_id == perception_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            SavedPerception(
                user_id=current_user.id,
                perception_id=perception_id,
            )
        )
        try:
            await db.commit()
        except IntegrityError:
            # Another request/device may have created the same save between
            # the existence check and commit. Save is intentionally idempotent.
            await db.rollback()

    return SaveToggleOut(saved=True)


@router.delete(
    "/perceptions/{perception_id}/save",
    response_model=SaveToggleOut,
)
async def unsave_perception(
    perception_id: int, current_user: CurrentUser, db: DbSession
):
    await _get_active_perception(perception_id, db)

    result = await db.execute(
        select(SavedPerception).where(
            SavedPerception.user_id == current_user.id,
            SavedPerception.perception_id == perception_id,
        )
    )
    saved = result.scalar_one_or_none()
    if saved is not None:
        await db.delete(saved)
        await db.commit()

    return SaveToggleOut(saved=False)


@router.get(
    "/users/me/saved-perceptions",
    response_model=list[PerceptionOut],
)
async def list_saved_perceptions(
    current_user: CurrentUser, db: DbSession
):
    result = await db.execute(
        select(Perception)
        .join(
            SavedPerception, SavedPerception.perception_id == Perception.id
        )
        .join(User, User.id == Perception.user_id)
        .where(
            SavedPerception.user_id == current_user.id,
            User.is_active.is_(True),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(SavedPerception.created_at.desc())
    )
    perceptions = list(result.scalars().all())
    return await bulk_to_out(db, perceptions, current_user.id)
