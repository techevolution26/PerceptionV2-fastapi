from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Notification
from app.services.broadcast import broadcast_notification

async def notify(db: AsyncSession, *, user_id: int, ntype: str, data: dict, commit: bool = True) -> Notification:
    payload = {"type": ntype, **data}
    note = Notification(user_id=user_id, type=ntype, data=payload)
    db.add(note)
    if commit:
        await db.commit(); await db.refresh(note)
    broadcast_notification(user_id,{"id":str(note.id),"read_at":None,"data":payload})
    return note
