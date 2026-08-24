# app/services/perception_serialization.py
from sqlalchemy import func, select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Comment, Like, Perception
from app.schemas.content import PerceptionOut


def _to_safe_dict(perception: Perception) -> dict:
    """
    Extracts raw database fields and eagerly checks loaded states using
    SQLAlchemy's inspector to completely isolate memory values from lazy loading traps.
    """
    # 1. Grab all raw primitive columns currently loaded in memory
    data = {
        key: value 
        for key, value in perception.__dict__.items() 
        if not key.startswith('_')
    }
    
    # 2. Use SQLAlchemy's inspector to check if relationships are actively loaded
    insp = inspect(perception)
    
    # Check 'user' relationship state safely
    if 'user' in insp.unloaded:
        data['user'] = None  # Not loaded in memory, pass None to schema validation
    else:
        data['user'] = perception.user # Loaded, safe to assign
        
    # Check 'topic' relationship state safely
    if 'topic' in insp.unloaded:
        data['topic'] = None
    else:
        data['topic'] = perception.topic
        
    return data


async def to_out(db: AsyncSession, perception: Perception, viewer_id: int | None) -> PerceptionOut:
    likes_count = (
        await db.execute(select(func.count()).select_from(Like).where(Like.perception_id == perception.id))
    ).scalar_one()
    comments_count = (
        await db.execute(select(func.count()).select_from(Comment).where(Comment.perception_id == perception.id))
    ).scalar_one()

    liked_by_user = False
    if viewer_id is not None:
        liked = await db.execute(
            select(Like.id).where(Like.perception_id == perception.id, Like.user_id == viewer_id)
        )
        liked_by_user = liked.scalar_one_or_none() is not None

    # Process via safe relationship dictionary inspector
    safe_data = _to_safe_dict(perception)
    
    return PerceptionOut(
        **PerceptionOut.model_validate(safe_data).model_dump(
            exclude={"likes_count", "comments_count", "liked_by_user"}
        ),
        likes_count=likes_count,
        comments_count=comments_count,
        liked_by_user=liked_by_user,
    )


async def bulk_to_out(db: AsyncSession, perceptions: list[Perception], viewer_id: int | None) -> list[PerceptionOut]:
    if not perceptions:
        return []
    ids = [p.id for p in perceptions]

    likes_rows = (
        await db.execute(
            select(Like.perception_id, func.count()).where(Like.perception_id.in_(ids)).group_by(Like.perception_id)
        )
    ).all()
    likes_map = dict(likes_rows)

    comments_rows = (
        await db.execute(
            select(Comment.perception_id, func.count())
            .where(Comment.perception_id.in_(ids))
            .group_by(Comment.perception_id)
        )
    ).all()
    comments_map = dict(comments_rows)

    liked_ids: set[int] = set()
    if viewer_id is not None:
        liked_rows = await db.execute(
            select(Like.perception_id).where(Like.perception_id.in_(ids), Like.user_id == viewer_id)
        )
        liked_ids = {row[0] for row in liked_rows.all()}

    out = []
    for p in perceptions:
        safe_data = _to_safe_dict(p)
        
        out.append(
            PerceptionOut(
                **PerceptionOut.model_validate(safe_data).model_dump(
                    exclude={"likes_count", "comments_count", "liked_by_user"}
                ),
                likes_count=likes_map.get(p.id, 0),
                comments_count=comments_map.get(p.id, 0),
                liked_by_user=p.id in liked_ids,
            )
        )
    return out
