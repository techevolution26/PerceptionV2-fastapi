# app/api/routes/notifications.py
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, DbSession
from app.models.models import Notification
from app.schemas.misc import NotificationOut, NotificationsListOut, UnreadCountOut

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationsListOut)
async def list_notifications(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notes = result.scalars().all()
    # Wrapped in {"data": [...]} to match NotificationsPanel.jsx, which reads
    # `payload.data`.
    return NotificationsListOut(data=[NotificationOut.model_validate(n) for n in notes])


@router.post("/notifications/read-all")
async def mark_all_read(current_user: CurrentUser, db: DbSession):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.delete(note)
    await db.commit()
    return {"message": "Deleted"}

@router.get("/notifications/unread-count", response_model=UnreadCountOut)
async def unread_count(current_user: CurrentUser, db: DbSession):
    return UnreadCountOut(count=int(await db.scalar(select(func.count(Notification.id)).where(Notification.user_id == current_user.id, Notification.read_at.is_(None))) or 0))
