# app/api/routes/comments.py

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import noload, selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.models import Comment, Perception
from app.schemas.content import CommentOut
from app.services.storage import ALLOWED_MEDIA_TYPES, save_upload

router = APIRouter(tags=["comments"])


def _load_options():
    """
    Eager-load the comment tree to the depth consumed by the clients.

    Supported response depth:

        root comment
        └── reply
            └── reply
                └── replies = []

    The third-level `replies` relationship is explicitly marked with
    `noload()` so Pydantic/FastAPI cannot trigger an async lazy-load
    during response serialization.

    This is important because the API uses SQLAlchemy's async session.
    Implicit lazy-loading during Pydantic serialization causes:

        sqlalchemy.exc.MissingGreenlet
    """

    return (
        # Root comment -> user
        selectinload(Comment.user),
        # Root comment -> replies -> user
        selectinload(Comment.replies).selectinload(Comment.user),
        # Root comment -> replies -> replies -> user
        selectinload(Comment.replies)
        .selectinload(Comment.replies)
        .selectinload(Comment.user),
        # Root comment -> replies -> replies -> replies
        #
        # Do not attempt to load another level. The frontend currently
        # renders two nested reply levels, so the terminal collection
        # should simply serialize as [].
        selectinload(Comment.replies)
        .selectinload(Comment.replies)
        .noload(Comment.replies),
    )


@router.get(
    "/perceptions/{perception_id}/comments",
    response_model=list[CommentOut],
)
async def list_comments(
    perception_id: int,
    db: DbSession,
):
    """
    Return the complete comment tree for a perception.

    All comments are fetched as a flat collection and then converted
    into a recursive Pydantic tree in memory.

    This supports arbitrary reply depth without recursive SQLAlchemy
    relationship loading and avoids MissingGreenlet with AsyncSession.
    """

    result = await db.execute(
        select(Comment)
        .where(Comment.perception_id == perception_id)
        .options(
            selectinload(Comment.user),
        )
        .order_by(Comment.created_at.asc())
    )

    comments = result.scalars().all()

    # Parent ID -> child comments
    children: dict[int | None, list[Comment]] = {}

    for comment in comments:
        children.setdefault(comment.parent_comment_id, []).append(comment)

    def build_comment(comment: Comment) -> CommentOut:
        return CommentOut(
            id=comment.id,
            perception_id=comment.perception_id,
            parent_comment_id=comment.parent_comment_id,
            body=comment.body,
            media_url=comment.media_url,
            created_at=comment.created_at,
            user=comment.user,
            replies=[build_comment(reply) for reply in children.get(comment.id, [])],
        )

    # Only root comments are returned at the top level.
    root_comments = children.get(None, [])

    # Existing behavior: newest root comments first.
    root_comments.sort(
        key=lambda comment: comment.created_at,
        reverse=True,
    )

    return [build_comment(comment) for comment in root_comments]



@router.post(
    "/perceptions/{perception_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    perception_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: str | None = Form(default=None),
    parent_comment_id: int | None = Form(default=None),
    media: UploadFile | None = File(default=None),
):
    """
    Create a comment on a perception.

    This endpoint also supports creating a reply when
    `parent_comment_id` is supplied.
    """

    if not body and media is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="body or media is required",
        )

    # Verify that the perception exists.
    perception_exists = await db.execute(
        select(Perception.id).where(
            Perception.id == perception_id,
        )
    )

    if perception_exists.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perception not found",
        )

    # If a parent comment was supplied, make sure it belongs to the
    # same perception. This prevents attaching a reply from another
    # perception to this one.
    if parent_comment_id is not None:
        parent_exists = await db.execute(
            select(Comment.id).where(
                Comment.id == parent_comment_id,
                Comment.perception_id == perception_id,
            )
        )

        if parent_exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )

    media_url = None

    if media is not None:
        media_url = await save_upload(
            media,
            "comments_media",
            allowed_types=ALLOWED_MEDIA_TYPES,
        )

    comment = Comment(
        user_id=current_user.id,
        perception_id=perception_id,
        parent_comment_id=parent_comment_id,
        body=body,
        media_url=media_url,
    )

    db.add(comment)

    await db.commit()

    # Do NOT access or assign `comment.replies` here.
    #
    # Accessing the relationship after commit can trigger an async
    # lazy-load and produce MissingGreenlet.
    #
    # Instead, query the newly-created record again with explicit
    # loading options.
    result = await db.execute(
        select(Comment)
        .where(Comment.id == comment.id)
        .options(
            selectinload(Comment.user),
            noload(Comment.replies),
        )
    )

    created_comment = result.scalar_one()

    return created_comment


@router.get(
    "/comments/{comment_id}/replies",
    response_model=list[CommentOut],
)
async def list_replies(
    comment_id: int,
    db: DbSession,
):
    """
    Return the replies belonging to a comment.

    The same eager-loading strategy is used so serialization never
    attempts an async lazy-load.
    """

    result = await db.execute(
        select(Comment).where(Comment.id == comment_id).options(*_load_options())
    )

    comment = result.scalar_one_or_none()

    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return comment.replies


@router.post(
    "/comments/{comment_id}/replies",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply(
    comment_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: str | None = Form(default=None),
    media: UploadFile | None = File(default=None),
):
    """
    Create a reply to an existing comment.
    """

    if not body and media is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="body or media is required",
        )

    # Load the parent comment.
    parent_result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
        )
    )

    parent_comment = parent_result.scalar_one_or_none()

    if parent_comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    media_url = None

    if media is not None:
        media_url = await save_upload(
            media,
            "comments_media",
            allowed_types=ALLOWED_MEDIA_TYPES,
        )

    reply = Comment(
        user_id=current_user.id,
        perception_id=parent_comment.perception_id,
        parent_comment_id=parent_comment.id,
        body=body,
        media_url=media_url,
    )

    db.add(reply)

    await db.commit()

    # Explicitly reload the created reply with the relationships needed
    # by CommentOut.
    #
    # `noload(Comment.replies)` guarantees that Pydantic sees an empty
    # replies collection instead of trying to lazy-load it.
    result = await db.execute(
        select(Comment)
        .where(Comment.id == reply.id)
        .options(
            selectinload(Comment.user),
            noload(Comment.replies),
        )
    )

    created_reply = result.scalar_one()

    return created_reply


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Delete a comment or reply.

    Deleting a parent comment also deletes its nested replies because
    `parent_comment_id` uses ON DELETE CASCADE.
    """

    result = await db.execute(select(Comment).where(Comment.id == comment_id))

    comment = result.scalar_one_or_none()

    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Replace these role checks with your project's existing
    # authorization helper if you already have one.
    is_owner = comment.user_id == current_user.id
    is_admin = getattr(current_user, "role", None) in {
        "ADMIN",
        "SUPER_ADMIN",
        "MODERATOR",
    }

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this comment",
        )

    await db.delete(comment)
    await db.commit()

    return None
