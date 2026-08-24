# app/api/routes/conversations.py
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text, update
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.models import Message, User
from app.schemas.misc import MessageOut, SendMessageRequest
from app.schemas.user import UserWithUnread
from app.services.broadcast import broadcast_new_message

router = APIRouter(tags=["conversations"])


class ConversationCreateRequest(BaseModel):
    peer_id: int
    body: str


@router.get("/conversations", response_model=list[UserWithUnread])
async def list_conversations(current_user: CurrentUser, db: DbSession):
    """
    Every user this account has ever exchanged a message with, each with an
    unread count and a last-message preview.

    Laravel's version only returned the unread count — no `lastMessage` /
    `lastMessagePreview` — even though ConversationSidebar.jsx and
    ConversationList.jsx both render them. Computed properly here via a
    Postgres DISTINCT ON to get the most recent message per peer in one
    query, then a second query for unread counts.
    """
    me = current_user.id

    last_message_rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (peer_id) peer_id, body, created_at
                FROM (
                    SELECT to_user_id AS peer_id, body, created_at
                    FROM messages WHERE from_user_id = :me
                    UNION ALL
                    SELECT from_user_id AS peer_id, body, created_at
                    FROM messages WHERE to_user_id = :me
                ) combined
                ORDER BY peer_id, created_at DESC
                """
            ),
            {"me": me},
        )
    ).all()

    if not last_message_rows:
        return []

    last_by_peer = {row.peer_id: row for row in last_message_rows}
    peer_ids = list(last_by_peer.keys())

    unread_rows = (
        await db.execute(
            select(Message.from_user_id, Message.id)
            .where(Message.to_user_id == me, Message.read_at.is_(None), Message.from_user_id.in_(peer_ids))
        )
    ).all()
    unread_count: dict[int, int] = {}
    for from_user_id, _ in unread_rows:
        unread_count[from_user_id] = unread_count.get(from_user_id, 0) + 1

    users_result = await db.execute(select(User).where(User.id.in_(peer_ids)))
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    out = []
    for peer_id in sorted(last_by_peer, key=lambda pid: last_by_peer[pid].created_at, reverse=True):
        user = users_by_id.get(peer_id)
        if user is None:
            continue
        last = last_by_peer[peer_id]
        preview = last.body if len(last.body) <= 80 else last.body[:77] + "…"
        out.append(
            UserWithUnread(
                id=user.id,
                name=user.name,
                avatar_url=user.avatar_url,
                profession=user.profession,
                unread=unread_count.get(peer_id, 0),
                lastMessage=last.created_at,
                lastMessagePreview=preview,
            )
        )
    return out


@router.get("/conversations/{peer_id}", response_model=list[MessageOut])
async def get_conversation(peer_id: int, current_user: CurrentUser, db: DbSession, page: int = 1, limit: int = 20):
    me = current_user.id

    peer_exists = await db.execute(select(User.id).where(User.id == peer_id))
    if peer_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    limit = max(1, min(limit, 100))
    offset = max(0, (page - 1) * limit)

    # Most recent `limit` messages, but returned oldest-first so the chat
    # window can just append them top-to-bottom without re-sorting.
    result = await db.execute(
        select(Message)
        .where(
            ((Message.from_user_id == me) & (Message.to_user_id == peer_id))
            | ((Message.from_user_id == peer_id) & (Message.to_user_id == me))
        )
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))

    await db.execute(
        update(Message)
        .where(Message.from_user_id == peer_id, Message.to_user_id == me, Message.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return messages


async def _send(db: DbSession, *, from_user_id: int, to_user_id: int, body: str) -> Message:
    to_exists = await db.execute(select(User.id).where(User.id == to_user_id))
    if to_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    message = Message(from_user_id=from_user_id, to_user_id=to_user_id, body=body)
    db.add(message)
    await db.commit()
    await db.refresh(message)

    broadcast_new_message(
        to_user_id,
        {
            "id": message.id,
            "from_user_id": message.from_user_id,
            "to_user_id": message.to_user_id,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        },
    )
    return message


@router.post("/conversations/{peer_id}", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(peer_id: int, payload: SendMessageRequest, current_user: CurrentUser, db: DbSession):
    return await _send(db, from_user_id=current_user.id, to_user_id=peer_id, body=payload.body)


@router.post("/conversations", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def start_conversation(payload: ConversationCreateRequest, current_user: CurrentUser, db: DbSession):
    return await _send(db, from_user_id=current_user.id, to_user_id=payload.peer_id, body=payload.body)
