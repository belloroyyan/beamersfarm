"""Secure owner-managed gallery image uploads."""

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def gallery_image_url(image_path):
    if not image_path or not image_path.startswith("uploads/gallery/"):
        return None
    filename = Path(image_path).name
    if not (Path(current_app.config["GALLERY_UPLOAD_FOLDER"]) / filename).is_file():
        return None
    return "/static/" + image_path


def save_gallery_image(upload):
    if not upload or not upload.filename:
        return None, "Choose a gallery image to upload."
    original = secure_filename(upload.filename)
    extension = Path(original).suffix.lower().lstrip(".")
    if not original or extension not in ALLOWED_EXTENSIONS:
        return None, "Use a JPG, JPEG, PNG, or WEBP gallery image."
    directory = Path(current_app.config["GALLERY_UPLOAD_FOLDER"])
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"gallery-{uuid4().hex}.{extension}"
    upload.save(directory / filename)
    return f"uploads/gallery/{filename}", None
