from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.models import InvestigationThread, Perception, PerceptionModeration
from app.schemas.investigation_threads import (
    InvestigationThreadCreate,
    InvestigationThreadListOut,
    InvestigationThreadOut,
    InvestigationThreadUpdate,
)

router = APIRouter(tags=["investigation threads"])


async def _get_public_perception(perception_id: int, db: DbSession) -> Perception:
    result = await db.execute(
        select(Perception)
        .join(PerceptionModeration, PerceptionModeration.perception_id == Perception.id, isouter=True)
        .where(
            Perception.id == perception_id,
            (PerceptionModeration.status.is_(None))
            | PerceptionModeration.status.in_(("published", "approved")),
        )
    )
    perception = result.scalar_one_or_none()
    if perception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")
    return perception


@router.get("/investigation-threads", response_model=InvestigationThreadListOut)
async def list_investigation_threads(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(InvestigationThread)
        .where(InvestigationThread.user_id == current_user.id)
        .order_by(InvestigationThread.updated_at.desc(), InvestigationThread.id.desc())
    )
    return InvestigationThreadListOut(items=list(result.scalars().all()))


@router.post(
    "/investigation-threads",
    response_model=InvestigationThreadOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_investigation_thread(
    payload: InvestigationThreadCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    await _get_public_perception(payload.perception_id, db)
    existing = await db.execute(
        select(InvestigationThread).where(
            InvestigationThread.user_id == current_user.id,
            InvestigationThread.perception_id == payload.perception_id,
            InvestigationThread.question == payload.question.strip(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This investigation path is already saved")

    thread = InvestigationThread(
        user_id=current_user.id,
        perception_id=payload.perception_id,
        title=payload.title.strip(),
        question=payload.question.strip(),
        rationale=payload.rationale.strip(),
        evidence_basis=payload.evidence_basis.strip(),
        validation_step=payload.validation_step.strip(),
        evidence_trace_id=payload.evidence_trace_id.strip() if payload.evidence_trace_id else None,
    )
    db.add(thread)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This investigation path is already saved") from None
    await db.refresh(thread)
    return thread


@router.patch("/investigation-threads/{thread_id}", response_model=InvestigationThreadOut)
async def update_investigation_thread(
    thread_id: int,
    payload: InvestigationThreadUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(InvestigationThread).where(
            InvestigationThread.id == thread_id,
            InvestigationThread.user_id == current_user.id,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation thread not found")
    if payload.status is not None:
        thread.status = payload.status
    if payload.note is not None:
        thread.note = payload.note.strip() or None
    await db.commit()
    await db.refresh(thread)
    return thread


@router.delete("/investigation-threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investigation_thread(thread_id: int, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(InvestigationThread).where(
            InvestigationThread.id == thread_id,
            InvestigationThread.user_id == current_user.id,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation thread not found")
    await db.delete(thread)
    await db.commit()
