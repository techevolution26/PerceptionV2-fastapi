# app/api/routes/topics.py
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.models import Topic, TopicFollow
from app.schemas.content import TopicOut, TopicsListOut
from app.schemas.misc import FollowToggleOut

router = APIRouter(tags=["topics"])


@router.get("/topics", response_model=TopicsListOut)
async def list_topics(db: DbSession):
    result = await db.execute(select(Topic).order_by(Topic.name))
    topics = result.scalars().all()
    # Wrapped in {"topics": [...]} to match the existing Next.js BFF proxy
    # (app/api/topics/route.js), which already unwraps `data.topics`.
    return TopicsListOut(topics=[TopicOut.model_validate(t) for t in topics])


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic(topic_id: int, db: DbSession):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return topic


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
        await db.commit()
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
