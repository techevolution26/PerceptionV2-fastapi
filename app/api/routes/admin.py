from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from app.api.deps import DbSession, SuperAdminUser
from app.models.models import AdminAuditLog, Comment, Like, Message, Perception, User

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: str


class AdminAuditOut(BaseModel):
    id: int
    actor_user_id: int
    actor_name: str
    target_user_id: int | None = None
    target_name: str | None = None
    action: str
    data: dict = Field(default_factory=dict)
    created_at: str


@router.get("/overview")
async def overview(admin: SuperAdminUser, db: DbSession):
    return {
        "users": int(await db.scalar(select(func.count(User.id))) or 0),
        "perceptions": int(await db.scalar(select(func.count(Perception.id))) or 0),
        "likes": int(await db.scalar(select(func.count(Like.id))) or 0),
        "comments": int(await db.scalar(select(func.count(Comment.id))) or 0),
        "messages": int(await db.scalar(select(func.count(Message.id))) or 0),
        "active_users": int(
            await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True)))
            or 0
        ),
    }


@router.get("/users", response_model=list[AdminUserOut])
async def users(admin: SuperAdminUser, db: DbSession, query: str = ""):
    stmt = select(User).order_by(User.created_at.desc()).limit(100)
    q = " ".join(query.split())[:80]
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)))
    users = (await db.execute(stmt)).scalars().all()
    return [
        AdminUserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]


@router.get("/audit", response_model=list[AdminAuditOut])
async def audit(
    admin: SuperAdminUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
):
    rows = (
        await db.execute(
            select(AdminAuditLog, User)
            .join(User, User.id == AdminAuditLog.actor_user_id)
            .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .limit(limit)
        )
    ).all()

    target_ids = {row[0].target_user_id for row in rows if row[0].target_user_id is not None}
    targets = {}
    if target_ids:
        target_rows = await db.execute(select(User.id, User.name).where(User.id.in_(target_ids)))
        targets = {user_id: name for user_id, name in target_rows.all()}

    return [
        AdminAuditOut(
            id=entry.id,
            actor_user_id=entry.actor_user_id,
            actor_name=actor.name,
            target_user_id=entry.target_user_id,
            target_name=targets.get(entry.target_user_id),
            action=entry.action,
            data=entry.data or {},
            created_at=entry.created_at.isoformat(),
        )
        for entry, actor in rows
    ]


@router.post("/users/{user_id}/suspend")
async def suspend(user_id: int, admin: SuperAdminUser, db: DbSession):
    if user_id == admin.id:
        raise HTTPException(400, "You cannot suspend your own admin account.")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "SUPER_ADMIN":
        active_super_admins = int(
            await db.scalar(
                select(func.count(User.id)).where(
                    User.role == "SUPER_ADMIN", User.is_active.is_(True)
                )
            )
            or 0
        )
        if active_super_admins <= 1:
            raise HTTPException(400, "The last active super administrator cannot be suspended.")
    if not user.is_active:
        return {"status": "suspended"}
    user.is_active = False
    user.token_version += 1
    db.add(
        AdminAuditLog(
            actor_user_id=admin.id,
            target_user_id=user.id,
            action="user.suspended",
            data={},
        )
    )
    await db.commit()
    return {"status": "suspended"}


@router.post("/users/{user_id}/restore")
async def restore(user_id: int, admin: SuperAdminUser, db: DbSession):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    if user.is_active:
        return {"status": "active"}
    user.is_active = True
    user.token_version += 1
    db.add(
        AdminAuditLog(
            actor_user_id=admin.id,
            target_user_id=user.id,
            action="user.restored",
            data={},
        )
    )
    await db.commit()
    return {"status": "active"}
