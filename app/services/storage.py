# app/services/storage.py
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


async def save_upload(file: UploadFile, subdir: str, *, allowed_types: set[str] | None = None) -> str:
    """Save an uploaded file under STORAGE_ROOT/<subdir>/ and return the
    public URL path (e.g. /storage/avatars/<uuid>.png), matching Laravel's
    `Storage::url()` convention that the frontend's next.config.js already
    rewrites `/storage/:path*` to hit.
    """
    if allowed_types and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported file type: {file.content_type}",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit",
        )

    ext = Path(file.filename or "").suffix.lower() or ""
    filename = f"{uuid.uuid4().hex}{ext}"

    target_dir = Path(settings.STORAGE_ROOT) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(contents)

    return f"{settings.STORAGE_URL_PREFIX}/{subdir}/{filename}"
