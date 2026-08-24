# app/api/routes/users.py
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.models import Comment, Follow, Like, Perception, Topic, TopicFollow, User
from app.schemas.content import PerceptionOut, TopicOut
from app.schemas.user import UpdateMeRequest, UserMe, UserProfile, UserSlim
from app.services.storage import ALLOWED_IMAGE_TYPES, save_upload

router = APIRouter(tags=["users"])


async def _profile_counts(db: DbSession, user_id: int) -> dict[str, int]:
    perceptions_count = (
        await db.execute(select(func.count()).select_from(Perception).where(Perception.user_id == user_id))
    ).scalar_one()
    followers_count = (
        await db.execute(select(func.count()).select_from(Follow).where(Follow.followed_id == user_id))
    ).scalar_one()
    following_count = (
        await db.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id))
    ).scalar_one()
    topics_count = (
        await db.execute(select(func.count()).select_from(TopicFollow).where(TopicFollow.user_id == user_id))
    ).scalar_one()
    return {
        "perceptions_count": perceptions_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "topics_count": topics_count,
    }


@router.get("/user", response_model=UserMe)
async def get_me(current_user: CurrentUser):
    return current_user


@router.put("/user", response_model=UserMe)
async def update_me(payload: UpdateMeRequest, current_user: CurrentUser, db: DbSession):
    if payload.name is not None:
        current_user.name = payload.name
    if payload.bio is not None:
        current_user.bio = payload.bio
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/user/profile", response_model=UserMe)
async def update_profile(
    current_user: CurrentUser,
    db: DbSession,
    profession: str | None = Form(default=None),
    bio: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
):
    if avatar is not None:
        current_user.avatar_url = await save_upload(avatar, "avatars", allowed_types=ALLOWED_IMAGE_TYPES)
    if profession is not None:
        current_user.profession = profession
    if bio is not None:
        current_user.bio = bio

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: int, db: DbSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    counts = await _profile_counts(db, user_id)
    return UserProfile(
        id=user.id,
        name=user.name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        profession=user.profession,
        created_at=user.created_at,
        **counts,
    )


@router.get("/users/{user_id}/perceptions", response_model=list[PerceptionOut])
async def get_user_perceptions(user_id: int, db: DbSession):
    exists = await db.execute(select(User.id).where(User.id == user_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(Perception)
        .where(Perception.user_id == user_id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .order_by(Perception.created_at.desc())
    )
    perceptions = result.scalars().all()

    out = []
    for p in perceptions:
        likes_count = (
            await db.execute(select(func.count()).select_from(Like).where(Like.perception_id == p.id))
        ).scalar_one()
        comments_count = (
            await db.execute(select(func.count()).select_from(Comment).where(Comment.perception_id == p.id))
        ).scalar_one()
        out.append(
            PerceptionOut(
                **PerceptionOut.model_validate(p).model_dump(exclude={"likes_count", "comments_count"}),
                likes_count=likes_count,
                comments_count=comments_count,
            )
        )
    return out


@router.get("/users/{user_id}/topics", response_model=list[TopicOut])
async def get_user_followed_topics(user_id: int, db: DbSession):
    result = await db.execute(
        select(Topic).join(TopicFollow, TopicFollow.topic_id == Topic.id).where(TopicFollow.user_id == user_id)
    )
    return result.scalars().all()


@router.post("/users/{user_id}/follow")
async def follow_user(user_id: int, current_user: CurrentUser, db: DbSession):
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow yourself")

    target = await db.execute(select(User.id).where(User.id == user_id))
    if target.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(Follow(follower_id=current_user.id, followed_id=user_id))
        await db.commit()

    return {"message": f"Now following user {user_id}"}


@router.delete("/users/{user_id}/follow")
async def unfollow_user(user_id: int, current_user: CurrentUser, db: DbSession):
    existing = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    follow = existing.scalar_one_or_none()
    if follow is not None:
        await db.delete(follow)
        await db.commit()
    return {"message": f"Unfollowed user {user_id}"}


@router.get("/users/{user_id}/followers", response_model=list[UserSlim])
async def get_followers(user_id: int, db: DbSession):
    result = await db.execute(
        select(User).join(Follow, Follow.follower_id == User.id).where(Follow.followed_id == user_id)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/following", response_model=list[UserSlim])
async def get_following(user_id: int, db: DbSession):
    result = await db.execute(
        select(User).join(Follow, Follow.followed_id == User.id).where(Follow.follower_id == user_id)
    )
    return result.scalars().all()


@router.get("/search-users", response_model=list[UserSlim])
async def search_users(db: DbSession, query: str = ""):
    if not query:
        return []
    like = f"%{query}%"
    result = await db.execute(
        select(User).where(
            (User.name.ilike(like)) | (User.email.ilike(like)) | (User.profession.ilike(like))
        ).limit(30)
    )
    return result.scalars().all()
