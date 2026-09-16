from fastapi import APIRouter, Query
from sqlalchemy import case, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Follow, Perception, Topic, User
from app.schemas.content import PerceptionOut
from app.schemas.user import UserSlim
from app.services.perception_serialization import bulk_to_out

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[PerceptionOut])
async def search(
    db: DbSession,
    viewer: OptionalUser,
    query: str = "",
    sort: str = Query(default="relevance", pattern="^(relevance|recent)$"),
    topic_id: int | None = Query(default=None, ge=1),
    user_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=50),
):
    """Refined perception search.

    Search relevance is based on textual/contextual matching, not engagement
    popularity. Optional topic/creator filters and recent ordering narrow the
    same canonical perception result contract used by the mobile clients.
    """
    q = " ".join(query.split())[:120]
    if len(q) < 2:
        return []

    like = f"%{q}%"
    prefix = f"{q}%"
    relevance = case(
        (Perception.body.ilike(prefix), 8),
        (Topic.name.ilike(prefix), 7),
        (User.name.ilike(prefix), 7),
        (User.profession.ilike(prefix), 6),
        (User.professional_focus.ilike(prefix), 6),
        (Perception.body.ilike(like), 3),
        (Topic.name.ilike(like), 3),
        (User.name.ilike(like), 3),
        (User.profession.ilike(like), 2),
        (User.professional_focus.ilike(like), 2),
        else_=0,
    )

    stmt = (
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .outerjoin(Topic, Topic.id == Perception.topic_id)
        .where(
            User.is_active.is_(True),
            or_(
                Perception.body.ilike(like),
                Topic.name.ilike(like),
                User.name.ilike(like),
                User.profession.ilike(like),
                User.professional_focus.ilike(like),
            ),
        )
        .options(selectinload(Perception.user), selectinload(Perception.topic))
    )

    if topic_id is not None:
        stmt = stmt.where(Perception.topic_id == topic_id)
    if user_id is not None:
        stmt = stmt.where(Perception.user_id == user_id)

    if sort == "recent":
        stmt = stmt.order_by(Perception.created_at.desc())
    else:
        stmt = stmt.order_by(relevance.desc(), Perception.created_at.desc())

    rows = await db.execute(stmt.limit(limit))
    return await bulk_to_out(db, list(rows.scalars().all()), viewer.id if viewer else None)


@router.get("/search-users", response_model=list[UserSlim])
async def search_users(db: DbSession, query: str = ""):
    q = " ".join(query.split())[:80]
    if len(q) < 2:
        return []
    like = f"%{q}%"
    return (
        await db.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                or_(
                    User.name.ilike(like),
                    User.profession.ilike(like),
                    User.professional_focus.ilike(like),
                ),
            )
            .order_by(User.name)
            .limit(30)
        )
    ).scalars().all()


@router.get("/messageable-users", response_model=list[UserSlim])
async def messageable_users(db: DbSession, current_user: CurrentUser, query: str = ""):
    stmt = select(User).join(Follow, Follow.followed_id == User.id).where(
        Follow.follower_id == current_user.id,
        User.id != current_user.id,
        User.is_active.is_(True),
        User.id.in_(select(Follow.follower_id).where(Follow.followed_id == current_user.id)),
    )
    q = " ".join(query.split())[:80]
    if len(q) >= 2:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.profession.ilike(like)))
    return (await db.execute(stmt.order_by(User.name).limit(30))).scalars().all()
