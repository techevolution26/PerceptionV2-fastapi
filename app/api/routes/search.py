from fastapi import APIRouter
from sqlalchemy import case, or_, select
from sqlalchemy.orm import selectinload
from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Follow, Perception, Topic, User
from app.schemas.content import PerceptionOut
from app.schemas.user import UserSlim
from app.services.perception_serialization import bulk_to_out
router=APIRouter(tags=["search"])
@router.get("/search",response_model=list[PerceptionOut])
async def search(db:DbSession,viewer:OptionalUser,query:str=""):
    q=" ".join(query.split())[:120]
    if len(q)<2:return []
    like=f"%{q}%"; relevance=case((Perception.body.ilike(f"{q}%"),5),(Topic.name.ilike(f"{q}%"),4),(User.name.ilike(f"{q}%"),4),(Perception.body.ilike(like),2),else_=1)
    rows=await db.execute(select(Perception).join(User,User.id==Perception.user_id).outerjoin(Topic,Topic.id==Perception.topic_id).where(or_(Perception.body.ilike(like),Topic.name.ilike(like),User.name.ilike(like),User.profession.ilike(like),User.professional_focus.ilike(like))).options(selectinload(Perception.user),selectinload(Perception.topic)).order_by(relevance.desc(),Perception.created_at.desc()).limit(50))
    return await bulk_to_out(db,list(rows.scalars().all()),viewer.id if viewer else None)
@router.get("/search-users",response_model=list[UserSlim])
async def search_users(db:DbSession,query:str=""):
    q=" ".join(query.split())[:80]
    if len(q)<2:return []
    like=f"%{q}%"; return (await db.execute(select(User).where(User.is_active.is_(True),or_(User.name.ilike(like),User.profession.ilike(like),User.professional_focus.ilike(like))).order_by(User.name).limit(30))).scalars().all()
@router.get("/messageable-users",response_model=list[UserSlim])
async def messageable_users(current_user:CurrentUser,db:DbSession,query:str=""):
    stmt=select(User).join(Follow,Follow.followed_id==User.id).where(Follow.follower_id==current_user.id,User.id!=current_user.id,User.is_active.is_(True),User.id.in_(select(Follow.follower_id).where(Follow.followed_id==current_user.id)))
    q=" ".join(query.split())[:80]
    if len(q)>=2: like=f"%{q}%"; stmt=stmt.where(or_(User.name.ilike(like),User.profession.ilike(like)))
    return (await db.execute(stmt.order_by(User.name).limit(30))).scalars().all()
