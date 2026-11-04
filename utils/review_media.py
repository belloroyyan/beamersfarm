from pathlib import Path
from uuid import uuid4
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_BYTES = 8 * 1024 * 1024
def save_review_image(upload):
    if not upload or not upload.filename: return None, None
    ext = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if ext not in IMAGE_EXTENSIONS: return None, "Use a JPG, PNG, or WEBP image under 8 MB."
    directory = Path(current_app.static_folder) / "uploads" / "reviews"; directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"review-{uuid4().hex}.{ext}"
    try:
        upload.save(target)
        if target.stat().st_size > MAX_BYTES: raise ValueError("Review images must be 8 MB or smaller.")
        with Image.open(target) as image: image.verify()
        return f"uploads/reviews/{target.name}", None
    except (OSError, UnidentifiedImageError, ValueError) as error:
        target.unlink(missing_ok=True); return None, str(error) if isinstance(error, ValueError) else "That image could not be uploaded."
def review_image_url(key):
    if not key or not isinstance(key, str) or not key.startswith("uploads/reviews/"): return None
    name = Path(key).name
    if not (Path(current_app.static_folder) / "uploads" / "reviews" / name).is_file(): return None
    return f"/static/uploads/reviews/{name}"
