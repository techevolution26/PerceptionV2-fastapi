# app/services/daily_digest.py
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.models import Comment, Like, Motivation, Perception, Topic, TopicFollow, User
from app.services.notifications import notify

logger = logging.getLogger("daily_digest")

HOT_THRESHOLD = 50


async def run_daily_digest() -> None:
    """
    One notification per user per day: a "hot" (50+ likes/comments) or
    otherwise-fresh perception from a topic they follow, posted in the last
    24h — or, failing that, a random motivational quote. Faithful port of
    the old `php artisan notify:daily` command (app/Console/Commands/
    NotifyDailyPerceptions.php), which ran on the same daily schedule.
    """
    logger.info("Running daily digest job")
    since = datetime.now(timezone.utc) - timedelta(days=1)

    async with AsyncSessionLocal() as db:
        user_ids = (await db.execute(select(User.id))).scalars().all()

        for user_id in user_ids:
            followed_topic_ids = (
                await db.execute(select(TopicFollow.topic_id).where(TopicFollow.user_id == user_id))
            ).scalars().all()

            sent = False
            if followed_topic_ids:
                fresh_result = await db.execute(
                    select(Perception)
                    .where(Perception.topic_id.in_(followed_topic_ids), Perception.created_at >= since)
                )
                fresh = fresh_result.scalars().all()

                if fresh:
                    hot: list[Perception] = []
                    for p in fresh:
                        likes = (
                            await db.execute(select(func.count()).select_from(Like).where(Like.perception_id == p.id))
                        ).scalar_one()
                        comments = (
                            await db.execute(
                                select(func.count()).select_from(Comment).where(Comment.perception_id == p.id)
                            )
                        ).scalar_one()
                        if likes >= HOT_THRESHOLD or comments >= HOT_THRESHOLD:
                            hot.append(p)

                    chosen = random.choice(hot) if hot else random.choice(fresh)

                    topic = await db.get(Topic, chosen.topic_id) if chosen.topic_id else None
                    await notify(
                        db,
                        user_id=user_id,
                        ntype="perception",
                        data={
                            "type": "perception",
                            "perception_id": chosen.id,
                            "body": chosen.body[:140],
                            "topic": topic.name if topic else "General",
                        },
                    )
                    sent = True

            if not sent:
                motivation_result = await db.execute(select(Motivation).order_by(func.random()).limit(1))
                motivation = motivation_result.scalar_one_or_none()
                if motivation is None:
                    continue
                topic = await db.get(Topic, motivation.topic_id) if motivation.topic_id else None
                await notify(
                    db,
                    user_id=user_id,
                    ntype="daily",
                    data={
                        "type": "daily",
                        "body": motivation.body,
                        "topic": topic.name if topic else "General",
                    },
                )

    logger.info("Daily digest job complete (%d users considered)", len(user_ids))
