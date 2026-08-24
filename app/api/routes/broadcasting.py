# app/api/routes/broadcasting.py
from fastapi import APIRouter, Form, HTTPException, status

from app.api.deps import CurrentUser
from app.services.broadcast import authenticate_channel

router = APIRouter(tags=["broadcasting"])


@router.post("/broadcasting/auth")
async def broadcasting_auth(
    current_user: CurrentUser,
    channel_name: str = Form(...),
    socket_id: str = Form(...),
):
    """
    Authorizes subscriptions to private channels, called by pusher-js
    whenever the frontend subscribes to a `private-*` channel (see
    NotificationsPanel.jsx / EchoContext.js). The only private channel this
    app uses is `private-App.Models.User.{id}` — a user's own notification
    stream — so a user may only ever authorize their own.
    """
    expected_prefix = "private-App.Models.User."
    if not channel_name.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown channel")

    channel_user_id = channel_name[len(expected_prefix):]
    if channel_user_id != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this channel")

    return authenticate_channel(channel_name, socket_id)
