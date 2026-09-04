from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from app.api.deps import DbSession, SuperAdminUser
from app.models.models import AdminAuditLog, Comment, Like, Message, Perception, User
from app.schemas.user import UserSlim

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.get("/users", response_model=list[UserSlim])
async def users(admin: SuperAdminUser, db: DbSession, query: str = ""):
    stmt = select(User).order_by(User.created_at.desc()).limit(100)
    q = " ".join(query.split())[:80]
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)))
    return (await db.execute(stmt)).scalars().all()


@router.post("/users/{user_id}/suspend")
async def suspend(user_id: int, admin: SuperAdminUser, db: DbSession):
    if user_id == admin.id:
        raise HTTPException(400, "You cannot suspend your own admin account.")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
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
