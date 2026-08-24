# app/services/broadcast.py
"""
Real-time layer. Speaks the Pusher HTTP protocol against soketi (a
self-hosted, open-source, Pusher-protocol-compatible WebSocket server run in
docker-compose). This means the frontend's existing `laravel-echo` +
`pusher-js` client code works completely unchanged — only the server
implementing the protocol has changed, from Laravel's broadcasting layer to
this thin wrapper.

Two channel conventions are preserved exactly as the frontend already
expects them:
  - Notifications: private channel `private-App.Models.User.{user_id}`,
    custom event name `.notification` (NOT Laravel's undocumented internal
    `illuminate:notification` event — see NotificationsPanel.jsx, which was
    updated to listen for a plain custom event instead of relying on
    Laravel-specific `laravel-echo` sugar that this backend doesn't produce).
  - Messages: public channel `conversations.{peer_id}`, event `NewMessage`.
"""
import logging

import pusher

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("broadcast")

_client = pusher.Pusher(
    app_id=settings.PUSHER_APP_ID,
    key=settings.PUSHER_APP_KEY,
    secret=settings.PUSHER_APP_SECRET,
    host=settings.PUSHER_HOST,
    port=settings.PUSHER_PORT,
    ssl=settings.PUSHER_SCHEME == "https",
    timeout=int(settings.UPSTREAM_TIMEOUT_SECONDS),
)


def _safe_trigger(channel: str, event: str, data: dict) -> None:
    """Broadcasting is best-effort: a soketi hiccup should never fail the
    HTTP request that triggered it (e.g. posting a message should still
    succeed and persist even if the live push fails — the recipient will
    still see it on next fetch)."""
    try:
        _client.trigger(channel, event, data)
    except Exception:  # noqa: BLE001
        logger.warning("Broadcast to %s/%s failed", channel, event, exc_info=True)


def broadcast_notification(user_id: int, notification: dict) -> None:
    # NOTE: no leading dot here — the dot in `.listen('.notification', cb)`
    # client-side is an Echo/Laravel convention meaning "don't namespace
    # this event", and gets stripped before binding. The literal wire event
    # name must match exactly what's triggered here: "notification".
    _safe_trigger(f"private-App.Models.User.{user_id}", "notification", notification)


def broadcast_new_message(peer_id: int, message: dict) -> None:
    _safe_trigger(f"conversations.{peer_id}", "NewMessage", {"message": message})


def authenticate_channel(channel_name: str, socket_id: str) -> dict:
    """Implements Pusher's private-channel auth handshake so
    POST /api/broadcasting/auth can authorize a subscription."""
    return _client.authenticate(channel=channel_name, socket_id=socket_id)
