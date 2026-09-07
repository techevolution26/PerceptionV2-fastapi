import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import get_settings

settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
_VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogg",
}


def _validate_image(contents: bytes, content_type: str) -> None:
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image.verify()
            detected = image.format
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid image file.") from exc

    expected = {"image/jpeg": "JPEG", "image/png": "PNG", "image/gif": "GIF", "image/webp": "WEBP"}[content_type]
    if detected != expected:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Image content does not match its declared type.")


def _validate_video(contents: bytes, content_type: str) -> None:
    if content_type == "video/mp4" and b"ftyp" not in contents[:64]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid MP4 file.")
    if content_type == "video/webm" and not contents.startswith(b"\x1a\x45\xdf\xa3"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid WebM file.")
    if content_type == "video/ogg" and not contents.startswith(b"OggS"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid Ogg file.")


async def save_upload(file: UploadFile, subdir: str, *, allowed_types: set[str] | None = None) -> str:
    content_type = (file.content_type or "").lower().strip()
    if allowed_types and content_type not in allowed_types:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unsupported file type.")

    contents = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")
    if not contents:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Uploaded file is empty.")

    if content_type in ALLOWED_IMAGE_TYPES:
        _validate_image(contents, content_type)
        extension = _IMAGE_EXTENSIONS[content_type]
    elif content_type in ALLOWED_VIDEO_TYPES:
        _validate_video(contents, content_type)
        extension = _VIDEO_EXTENSIONS[content_type]
    else:
        extension = Path(file.filename or "").suffix.lower()
        if not extension:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unsupported file type.")

    filename = f"{uuid.uuid4().hex}{extension}"
    target_dir = Path(settings.STORAGE_ROOT) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_bytes(contents)
    return f"{settings.STORAGE_URL_PREFIX}/{subdir}/{filename}"
