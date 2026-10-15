"""Safe gallery media management for photos and browser-playable videos."""
from pathlib import Path
from uuid import uuid4
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024

def _gallery_directory(): return Path(current_app.static_folder) / "uploads" / "gallery"
def gallery_image_url(image_key):
    if not image_key or not isinstance(image_key, str): return None
    key = Path(image_key)
    if key.parent.as_posix() != "uploads/gallery" or key.name != image_key.rsplit("/", 1)[-1]: return None
    if not (_gallery_directory() / key.name).is_file(): return None
    return f"/static/uploads/gallery/{key.name}"
def gallery_media_type(image_key): return "video" if Path(image_key or "").suffix.lower().lstrip(".") in VIDEO_EXTENSIONS else "image"
def save_gallery_media(upload):
    if not upload or not upload.filename: return None, None, None
    original = secure_filename(upload.filename); ext = Path(original).suffix.lower().lstrip(".")
    if ext in VIDEO_EXTENSIONS:
        destination = _gallery_directory() / f"gallery-{uuid4().hex}.{ext}"; _gallery_directory().mkdir(parents=True, exist_ok=True)
        try:
            upload.save(destination)
            if destination.stat().st_size > MAX_VIDEO_BYTES: raise ValueError("Videos must be 80 MB or smaller.")
            return f"uploads/gallery/{destination.name}", "video", None
        except (OSError, ValueError) as error:
            destination.unlink(missing_ok=True); return None, None, str(error)
    if ext not in {"jpg", "jpeg", "png", "webp"}: return None, None, "Use JPG, PNG, WEBP, MP4, WEBM, or MOV files."
    directory = _gallery_directory(); directory.mkdir(parents=True, exist_ok=True); temporary = directory / f"upload-{uuid4().hex}.tmp"
    try:
        upload.save(temporary)
        if temporary.stat().st_size > MAX_IMAGE_BYTES: raise ValueError("Images must be 8 MB or smaller.")
        with Image.open(temporary) as image:
            if image.format not in IMAGE_FORMATS or image.width * image.height > 30_000_000: raise ValueError("The selected image is not supported or is too large.")
            image.verify()
        filename = f"gallery-{uuid4().hex}.{IMAGE_FORMATS[image.format]}"; destination = directory / filename; temporary.replace(destination)
        return f"uploads/gallery/{filename}", "image", None
    except (OSError, UnidentifiedImageError, ValueError) as error:
        temporary.unlink(missing_ok=True); return None, None, str(error) if isinstance(error, ValueError) else "The selected image is invalid."
def save_gallery_image(upload):
    key, media_type, error = save_gallery_media(upload); return key, error
def delete_gallery_image(image_key):
    if not image_key or not isinstance(image_key, str): return
    key = Path(image_key)
    if key.parent.as_posix() == "uploads/gallery":
        path = _gallery_directory() / key.name
        if path.is_file(): path.unlink()
