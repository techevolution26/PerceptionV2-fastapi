from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Notification, User
from app.services.broadcast import broadcast_notification

async def notify(db: AsyncSession, *, user_id: int, ntype: str, data: dict, commit: bool = True) -> Notification:
    user = await db.get(User, user_id)
    preferences = dict(user.notification_preferences or {}) if user else {}
    preference_key = {
        "perception_like": "likes",
        "perception_comment": "comments",
        "comment_reply": "comments",
        "follow": "follows",
        "message": "messages",
    }.get(ntype, "system")
    if preferences.get(preference_key) is False:
        # Preference changes affect future notifications only.
        return Notification(user_id=user_id, type=ntype, data={"type": ntype, **data})

    payload = {"type": ntype, **data}
    note = Notification(user_id=user_id, type=ntype, data=payload)
    db.add(note)
    if commit:
        await db.commit(); await db.refresh(note)
    broadcast_notification(user_id,{"id":str(note.id),"read_at":None,"data":payload})
    return note
