from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, DbSession
from app.models.models import AdminAuditLog, Perception, PerceptionModeration, Topic, User
from app.schemas.perception_moderation import PerceptionModerationDecision, PerceptionModerationStatus

router = APIRouter(tags=["perception-moderation"])


class ModerationQueueItem(BaseModel):
    perception_id: int
    body: str
    topic_id: int | None
    topic_name: str | None
    author_id: int
    author_name: str
    status: PerceptionModerationStatus
    risk_level: str
    flags: list[str] = Field(default_factory=list)
    checked_at: datetime
    created_at: datetime


@router.get("/admin/perceptions/review", response_model=list[ModerationQueueItem])
async def moderation_queue(
    admin: AdminUser,
    db: DbSession,
    status_filter: PerceptionModerationStatus = Query(
        default=PerceptionModerationStatus.PENDING_REVIEW,
        alias="status",
    ),
    limit: int = Query(default=50, ge=1, le=100),
):
    rows = await db.execute(
        select(PerceptionModeration, Perception, User, Topic)
        .join(Perception, Perception.id == PerceptionModeration.perception_id)
        .join(User, User.id == Perception.user_id)
        .outerjoin(Topic, Topic.id == Perception.topic_id)
        .where(PerceptionModeration.status == status_filter.value)
        .order_by(PerceptionModeration.checked_at.asc(), PerceptionModeration.id.asc())
        .limit(limit)
    )
    return [
        ModerationQueueItem(
            perception_id=moderation.perception_id,
            body=perception.body,
            topic_id=perception.topic_id,
            topic_name=topic.name if topic else None,
            author_id=author.id,
            author_name=author.name,
            status=moderation.status,
            risk_level=moderation.risk_level,
            flags=list(moderation.flags or []),
            checked_at=moderation.checked_at,
            created_at=perception.created_at,
        )
        for moderation, perception, author, topic in rows.all()
    ]


@router.patch("/admin/perceptions/{perception_id}/review", response_model=ModerationQueueItem)
async def review_perception(
    perception_id: int,
    payload: PerceptionModerationDecision,
    admin: AdminUser,
    db: DbSession,
):
    moderation = await db.scalar(
        select(PerceptionModeration).where(PerceptionModeration.perception_id == perception_id)
    )
    if moderation is None:
        raise HTTPException(404, "Moderation record not found")
    if moderation.status != PerceptionModerationStatus.PENDING_REVIEW.value:
        raise HTTPException(409, "This perception has already been reviewed.")
    if payload.status not in {
        PerceptionModerationStatus.APPROVED,
        PerceptionModerationStatus.REMOVED,
    }:
        raise HTTPException(400, "A review must approve or remove the perception.")

    moderation.status = payload.status.value
    moderation.reviewed_by_user_id = admin.id
    moderation.reviewed_at = datetime.now(timezone.utc)
    moderation.review_note = payload.review_note.strip() if payload.review_note else None
    db.add(
        AdminAuditLog(
            actor_user_id=admin.id,
            action="perception.moderation.reviewed",
            data={
                "perception_id": perception_id,
                "status": moderation.status,
                "risk_level": moderation.risk_level,
                "flags": list(moderation.flags or []),
            },
        )
    )
    await db.commit()

    row = await db.execute(
        select(PerceptionModeration, Perception, User, Topic)
        .join(Perception, Perception.id == PerceptionModeration.perception_id)
        .join(User, User.id == Perception.user_id)
        .outerjoin(Topic, Topic.id == Perception.topic_id)
        .where(PerceptionModeration.perception_id == perception_id)
    )
    moderation, perception, author, topic = row.one()
    return ModerationQueueItem(
        perception_id=moderation.perception_id,
        body=perception.body,
        topic_id=perception.topic_id,
        topic_name=topic.name if topic else None,
        author_id=author.id,
        author_name=author.name,
        status=moderation.status,
        risk_level=moderation.risk_level,
        flags=list(moderation.flags or []),
        checked_at=moderation.checked_at,
        created_at=perception.created_at,
    )
