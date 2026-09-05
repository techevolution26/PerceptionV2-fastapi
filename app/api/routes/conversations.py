from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, text
from app.api.deps import CurrentUser, DbSession
from app.models.models import ConversationState, Follow, Message, User
from app.schemas.misc import (
    ConversationActionOut,
    EditMessageRequest,
    MessageOut,
    SendMessageRequest,
)
from app.schemas.user import UserWithUnread
from app.services.broadcast import broadcast_message_update, broadcast_new_message
from app.services.notifications import notify

router = APIRouter(tags=["conversations"])
WINDOW = timedelta(minutes=15)


class ConversationCreateRequest(BaseModel):
    peer_id: int
    body: str


async def _mutual(db, me, peer):
    pairs = set(
        (
            await db.execute(
                select(Follow.follower_id, Follow.followed_id).where(
                    ((Follow.follower_id == me) & (Follow.followed_id == peer))
                    | ((Follow.follower_id == peer) & (Follow.followed_id == me))
                )
            )
        ).all()
    )
    return (me, peer) in pairs and (peer, me) in pairs


async def _exists(db, me, peer):
    return (
        await db.scalar(
            select(Message.id)
            .where(
                ((Message.from_user_id == me) & (Message.to_user_id == peer))
                | ((Message.from_user_id == peer) & (Message.to_user_id == me))
            )
            .limit(1)
        )
    ) is not None


@router.get("/conversations", response_model=list[UserWithUnread])
async def list_conversations(
    current_user: CurrentUser, db: DbSession, archived: bool = False
):
    me = current_user.id
    state = (
        "AND cs.archived_at IS NOT NULL" if archived else "AND cs.archived_at IS NULL"
    )
    rows = await db.execute(
        text(f"""
            SELECT DISTINCT ON (c.peer_id)
                c.peer_id,
                c.body,
                c.created_at
            FROM (
                SELECT
                    to_user_id AS peer_id,
                    body,
                    created_at
                FROM messages
                WHERE from_user_id = :me

                UNION ALL

                SELECT
                    from_user_id AS peer_id,
                    body,
                    created_at
                FROM messages
                WHERE to_user_id = :me
            ) c
            LEFT JOIN conversation_states cs
                ON cs.user_id = :me
                AND cs.peer_id = c.peer_id
            WHERE cs.deleted_at IS NULL
            {state}
            ORDER BY c.peer_id, c.created_at DESC
            """),
        {"me": me},
    )
    last = {r.peer_id: r for r in rows.all()}
    ids = list(last)
    if not ids:
        return []
    unread = {}
    for uid, _ in (
        await db.execute(
            select(Message.from_user_id, Message.id).where(
                Message.to_user_id == me,
                Message.read_at.is_(None),
                Message.from_user_id.in_(ids),
            )
        )
    ).all():
        unread[uid] = unread.get(uid, 0) + 1
    users = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(ids))))
        .scalars()
        .all()
    }
    return [
        UserWithUnread(
            id=users[x].id,
            name=users[x].name,
            avatar_url=users[x].avatar_url,
            profession=users[x].profession,
            unread=unread.get(x, 0),
            lastMessage=last[x].created_at,
            lastMessagePreview=(
                last[x].body if len(last[x].body) <= 80 else last[x].body[:77] + "…"
            ),
        )
        for x in sorted(last, key=lambda k: last[k].created_at, reverse=True)
        if x in users
    ]


@router.get("/conversations/{peer_id}", response_model=list[MessageOut])
async def get_conversation(
    peer_id: int,
    current_user: CurrentUser,
    db: DbSession,
    page: int = 1,
    limit: int = 30,
):
    if (
        peer_id == current_user.id
        or await db.scalar(select(User.id).where(User.id == peer_id)) is None
    ):
        raise HTTPException(404, "Conversation user not found")
    limit = max(1, min(limit, 100))
    result = await db.execute(
        select(Message)
        .where(
            (
                (Message.from_user_id == current_user.id)
                & (Message.to_user_id == peer_id)
            )
            | (
                (Message.from_user_id == peer_id)
                & (Message.to_user_id == current_user.id)
            )
        )
        .order_by(Message.created_at.desc())
        .offset(max(0, (page - 1) * limit))
        .limit(limit)
    )
    msgs = list(reversed(result.scalars().all()))
    await db.execute(
        update(Message)
        .where(
            Message.from_user_id == peer_id,
            Message.to_user_id == current_user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return msgs


async def _send(db, me, peer, body):
    body = body.strip()
    if not body:
        raise HTTPException(422, "Message cannot be empty")
    if me == peer:
        raise HTTPException(400, "You cannot message yourself")
    if await db.scalar(select(User.id).where(User.id == peer)) is None:
        raise HTTPException(404, "User not found")
    if not await _exists(db, me, peer) and not await _mutual(db, me, peer):
        raise HTTPException(403, "Messaging opens when you both follow each other.")
    for uid, pid in ((me, peer), (peer, me)):
        st = await db.scalar(
            select(ConversationState).where(
                ConversationState.user_id == uid, ConversationState.peer_id == pid
            )
        )
        if st:
            st.deleted_at = None
            st.archived_at = None
    msg = Message(from_user_id=me, to_user_id=peer, body=body)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    payload = {
        "id": msg.id,
        "from_user_id": msg.from_user_id,
        "to_user_id": msg.to_user_id,
        "body": msg.body,
        "created_at": msg.created_at.isoformat(),
        "read_at": None,
    }
    broadcast_new_message(peer, payload)
    await notify(
        db,
        user_id=peer,
        ntype="message",
        data={
            "message_id": msg.id,
            "from_user_id": me,
            "actor_name": (await db.scalar(select(User.name).where(User.id == me)))
            or "Someone",
            "body": body[:120],
        },
        commit=True,
    )
    return msg


@router.post("/conversations/{peer_id}", response_model=MessageOut, status_code=201)
async def send(
    peer_id: int, payload: SendMessageRequest, current_user: CurrentUser, db: DbSession
):
    return await _send(db, current_user.id, peer_id, payload.body)


@router.post("/conversations", response_model=MessageOut, status_code=201)
async def start(
    payload: ConversationCreateRequest, current_user: CurrentUser, db: DbSession
):
    return await _send(db, current_user.id, payload.peer_id, payload.body)


@router.patch("/messages/{message_id}", response_model=MessageOut)
async def edit(
    message_id: int,
    payload: EditMessageRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    msg = await db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.from_user_id == current_user.id,
            Message.deleted_at.is_(None),
        )
    )
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.created_at < datetime.now(timezone.utc) - WINDOW:
        raise HTTPException(409, "The edit window has closed.")
    body = payload.body.strip()
    if not body:
        raise HTTPException(422, "Message cannot be empty")
    msg.body = body
    msg.edited_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    broadcast_message_update(
        msg.to_user_id,
        {
            "id": msg.id,
            "from_user_id": msg.from_user_id,
            "to_user_id": msg.to_user_id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            "deleted_at": None,
        },
    )
    return msg


@router.delete("/messages/{message_id}", response_model=MessageOut)
async def recall(message_id: int, current_user: CurrentUser, db: DbSession):
    msg = await db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.from_user_id == current_user.id,
            Message.deleted_at.is_(None),
        )
    )
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.created_at < datetime.now(timezone.utc) - WINDOW:
        raise HTTPException(409, "The recall window has closed.")
    msg.body = "Message recalled"
    msg.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    broadcast_message_update(
        msg.to_user_id,
        {
            "id": msg.id,
            "from_user_id": msg.from_user_id,
            "to_user_id": msg.to_user_id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
        },
    )
    return msg


@router.post("/conversations/{peer_id}/archive", response_model=ConversationActionOut)
async def archive(peer_id: int, current_user: CurrentUser, db: DbSession):
    if (
        peer_id == current_user.id
        or await db.scalar(select(User.id).where(User.id == peer_id)) is None
    ):
        raise HTTPException(404, "Conversation user not found")
    st = await db.scalar(
        select(ConversationState).where(
            ConversationState.user_id == current_user.id,
            ConversationState.peer_id == peer_id,
        )
    )
    if st is None:
        st = ConversationState(user_id=current_user.id, peer_id=peer_id)
        db.add(st)
    st.archived_at = datetime.now(timezone.utc)
    st.deleted_at = None
    await db.commit()
    return ConversationActionOut(archived=True)


@router.delete("/conversations/{peer_id}", response_model=ConversationActionOut)
async def delete(peer_id: int, current_user: CurrentUser, db: DbSession):
    if (
        peer_id == current_user.id
        or await db.scalar(select(User.id).where(User.id == peer_id)) is None
    ):
        raise HTTPException(404, "Conversation user not found")
    st = await db.scalar(
        select(ConversationState).where(
            ConversationState.user_id == current_user.id,
            ConversationState.peer_id == peer_id,
        )
    )
    if st is None:
        st = ConversationState(user_id=current_user.id, peer_id=peer_id)
        db.add(st)
    st.deleted_at = datetime.now(timezone.utc)
    st.archived_at = None
    await db.commit()
    return ConversationActionOut(deleted=True)
