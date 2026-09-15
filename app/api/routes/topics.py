# app/api/routes/topics.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.models import Topic, TopicFollow
from app.schemas.content import TopicOut, TopicsListOut
from app.schemas.misc import FollowToggleOut

router = APIRouter(tags=["topics"])


@router.get("/topics", response_model=TopicsListOut)
async def list_topics(db: DbSession, viewer: OptionalUser):
    result = await db.execute(
        select(
            Topic,
            func.count(TopicFollow.user_id).label("followers_count"),
        )
        .outerjoin(TopicFollow, TopicFollow.topic_id == Topic.id)
        .group_by(Topic.id)
        .order_by(Topic.name)
    )
    rows = result.all()

    followed_ids: set[int] = set()
    if viewer is not None:
        followed = await db.execute(
            select(TopicFollow.topic_id).where(TopicFollow.user_id == viewer.id)
        )
        followed_ids = set(followed.scalars().all())

    topics = [
        TopicOut(
            id=topic.id,
            name=topic.name,
            description=topic.description,
            image_url=topic.image_url,
            followers_count=int(followers_count),
            followed_by_user=topic.id in followed_ids,
        )
        for topic, followers_count in rows
    ]
    # Wrapped in {"topics": [...]} to match the existing Next.js BFF proxy
    # (app/api/topics/route.js), which already unwraps `data.topics`.
    return TopicsListOut(topics=topics)


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic(topic_id: int, db: DbSession, viewer: OptionalUser):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    followers_count = await db.scalar(
        select(func.count(TopicFollow.user_id)).where(TopicFollow.topic_id == topic_id)
    )
    followed_by_user = False
    if viewer is not None:
        followed_by_user = (
            await db.scalar(
                select(TopicFollow.topic_id).where(
                    TopicFollow.user_id == viewer.id,
                    TopicFollow.topic_id == topic_id,
                )
            )
        ) is not None

    return TopicOut(
        id=topic.id,
        name=topic.name,
        description=topic.description,
        image_url=topic.image_url,
        followers_count=int(followers_count or 0),
        followed_by_user=followed_by_user,
    )


@router.post("/topics/{topic_id}/follow", response_model=FollowToggleOut)
async def follow_topic(topic_id: int, current_user: CurrentUser, db: DbSession):
    exists = await db.execute(select(Topic.id).where(Topic.id == topic_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    existing = await db.execute(
        select(TopicFollow).where(TopicFollow.user_id == current_user.id, TopicFollow.topic_id == topic_id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(TopicFollow(user_id=current_user.id, topic_id=topic_id))
        try:
            await db.commit()
        except IntegrityError:
            # The composite primary key is the final concurrency guard. A
            # simultaneous follow is already the desired end state.
            await db.rollback()
    return FollowToggleOut(followed=True)


@router.delete("/topics/{topic_id}/follow", response_model=FollowToggleOut)
async def unfollow_topic(topic_id: int, current_user: CurrentUser, db: DbSession):
    existing = await db.execute(
        select(TopicFollow).where(TopicFollow.user_id == current_user.id, TopicFollow.topic_id == topic_id)
    )
    follow = existing.scalar_one_or_none()
    if follow is not None:
        await db.delete(follow)
        await db.commit()
    return FollowToggleOut(followed=False)
