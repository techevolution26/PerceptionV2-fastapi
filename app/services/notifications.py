# app/services/notifications.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification
from app.services.broadcast import broadcast_notification


async def notify(db: AsyncSession, *, user_id: int, ntype: str, data: dict, commit: bool = True) -> Notification:
    """Create a notification row and push it live — mirrors Laravel's
    `$user->notify(...)` which wrote to the `database` and `broadcast`
    channels simultaneously (see app/Notifications/*.php in the old repo)."""
    note = Notification(user_id=user_id, type=ntype, data=data)
    db.add(note)
    if commit:
        await db.commit()
        await db.refresh(note)

    broadcast_notification(
        user_id,
        {
            "id": str(note.id),
            "read_at": None,
            "data": data,
        },
    )
    return note
