"""Safe image management helpers for the customer-facing farm gallery."""

from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

MAX_GALLERY_IMAGE_BYTES = 8 * 1024 * 1024
MAX_GALLERY_IMAGE_PIXELS = 30_000_000
_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _gallery_directory():
    return Path(current_app.static_folder) / "uploads" / "gallery"


def gallery_image_url(image_key):
    if not image_key or not isinstance(image_key, str):
        return None
    key = Path(image_key)
    if key.parent.as_posix() != "uploads/gallery" or key.name != image_key.rsplit("/", 1)[-1]:
        return None
    if not (_gallery_directory() / key.name).is_file():
        return None
    return f"/static/uploads/gallery/{key.name}"


def save_gallery_image(upload):
    if not upload or not upload.filename:
        return None, None
    original = secure_filename(upload.filename)
    if not original:
        return None, "Choose a valid JPG, PNG or WEBP image."
    directory = _gallery_directory()
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f"upload-{uuid4().hex}.tmp"
    try:
        upload.save(temporary)
        if temporary.stat().st_size > MAX_GALLERY_IMAGE_BYTES:
            raise ValueError("Gallery images must be 8 MB or smaller.")
        with Image.open(temporary) as image:
            image_format = image.format
            width, height = image.size
            if image_format not in _FORMATS:
                raise ValueError("Use a JPG, PNG or WEBP image.")
            if width <= 0 or height <= 0 or width * height > MAX_GALLERY_IMAGE_PIXELS:
                raise ValueError("The uploaded image dimensions are too large.")
            image.verify()
        extension = _FORMATS[image_format]
        filename = f"gallery-{uuid4().hex}.{extension}"
        destination = directory / filename
        temporary.replace(destination)
        return f"uploads/gallery/{filename}", None
    except (OSError, UnidentifiedImageError, ValueError) as error:
        temporary.unlink(missing_ok=True)
        return None, str(error) if isinstance(error, ValueError) else "The selected file is not a valid JPG, PNG or WEBP image."


def delete_gallery_image(image_key):
    if not image_key or not isinstance(image_key, str):
        return
    key = Path(image_key)
    if key.parent.as_posix() != "uploads/gallery":
        return
    path = _gallery_directory() / key.name
    if path.is_file():
        path.unlink()
