"""Product image URLs and secure owner-upload handling."""

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

PRODUCT_IMAGE_URLS = {
    "full": "/manus-storage/async-images/CSkhU0ccI2VBEBmjjf2dFa/image-1.webp",
    "laps": "/manus-storage/async-images/CSkhU0ccI2VBEBmjjf2dFa/image-2.webp",
    "drumsticks": "/manus-storage/async-images/CSkhU0ccI2VBEBmjjf2dFa/image-3.webp",
}
ALLOWED_PRODUCT_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def product_image_url(image_key):
    if image_key and image_key.startswith("uploads/products/"):
        if not (Path(current_app.config["PRODUCT_UPLOAD_FOLDER"]) / Path(image_key).name).is_file():
            return PRODUCT_IMAGE_URLS["full"]
        return "/static/" + image_key
    return PRODUCT_IMAGE_URLS.get(image_key, PRODUCT_IMAGE_URLS["full"])


def save_product_image(upload):
    """Save an optional owner upload and return its database-relative path."""
    if not upload or not upload.filename:
        return None, None
    original = secure_filename(upload.filename)
    extension = Path(original).suffix.lower().lstrip(".")
    if not original or extension not in ALLOWED_PRODUCT_IMAGE_EXTENSIONS:
        return None, "Use a JPG, JPEG, PNG, or WEBP product image."
    upload_dir = Path(current_app.config["PRODUCT_UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"product-{uuid4().hex}.{extension}"
    upload.save(upload_dir / filename)
    return f"uploads/products/{filename}", None
