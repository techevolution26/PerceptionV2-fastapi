# app/api/routes/comments.py
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.models import Comment, Perception
from app.schemas.content import CommentOut
from app.services.storage import ALLOWED_MEDIA_TYPES, save_upload

router = APIRouter(tags=["comments"])


def _load_options():
    # Two levels of nested replies eager-loaded — matches the depth the
    # frontend's CommentsList component actually renders.
    return (
        selectinload(Comment.user),
        selectinload(Comment.replies).selectinload(Comment.user),
        selectinload(Comment.replies).selectinload(Comment.replies).selectinload(Comment.user),
    )


@router.get("/perceptions/{perception_id}/comments", response_model=list[CommentOut])
async def list_comments(perception_id: int, db: DbSession):
    result = await db.execute(
        select(Comment)
        .where(Comment.perception_id == perception_id, Comment.parent_comment_id.is_(None))
        .options(*_load_options())
        .order_by(Comment.created_at.desc())
    )
    return result.scalars().all()


@router.post("/perceptions/{perception_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    perception_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: str | None = Form(default=None),
    parent_comment_id: int | None = Form(default=None),
    media: UploadFile | None = File(default=None),
):
    if not body and media is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="body or media is required")

    perception_exists = await db.execute(select(Perception.id).where(Perception.id == perception_id))
    if perception_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perception not found")

    media_url = None
    if media is not None:
        media_url = await save_upload(media, "comments_media", allowed_types=ALLOWED_MEDIA_TYPES)

    comment = Comment(
        user_id=current_user.id,
        perception_id=perception_id,
        parent_comment_id=parent_comment_id,
        body=body,
        media_url=media_url,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment, attribute_names=["user"])
    comment.replies = []
    return comment


@router.get("/comments/{comment_id}/replies", response_model=list[CommentOut])
async def list_replies(comment_id: int, db: DbSession):
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id).options(*_load_options())
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment.replies


@router.post("/comments/{comment_id}/replies", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_reply(
    comment_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: str | None = Form(default=None),
    media: UploadFile | None = File(default=None),
):
    if not body and media is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="body or media is required")

    parent = await db.execute(select(Comment).where(Comment.id == comment_id))
    parent_comment = parent.scalar_one_or_none()
    if parent_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    media_url = None
    if media is not None:
        media_url = await save_upload(media, "comments_media", allowed_types=ALLOWED_MEDIA_TYPES)

    reply = Comment(
        user_id=current_user.id,
        perception_id=parent_comment.perception_id,
        parent_comment_id=parent_comment.id,
        body=body,
        media_url=media_url,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply, attribute_names=["user"])
    reply.replies = []
    return reply
