"""Utilities for independent supplier advertisements and their uploaded images."""

import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_PARTNER_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def normalize_http_url(value, field_name="URL"):
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > 500:
        raise ValueError(f"{field_name} must be 500 characters or fewer.")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ValueError(f"{field_name} must begin with http:// or https:// and include a valid host.")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not contain embedded login credentials.")
    return value


def parse_social_links(raw_text):
    """Parse up to ten lines: `Label | https://...` (or just a URL)."""
    links = []
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    if len(lines) > 10:
        raise ValueError("Add no more than 10 social/profile links.")
    for line in lines:
        if "|" in line:
            label, url = (part.strip() for part in line.split("|", 1))
        else:
            label, url = "", line
        url = normalize_http_url(url, "Social/profile link")
        if not label:
            label = urlsplit(url).hostname or "Social link"
        if len(label) > 60:
            raise ValueError("Each social link label must be 60 characters or fewer.")
        links.append({"label": label, "url": url})
    return json.dumps(links, ensure_ascii=False)


def social_links_text(listing):
    return "\n".join(f"{item['label']} | {item['url']}" for item in listing.social_links)


def _partner_upload_dir():
    return Path(current_app.root_path) / "static" / "uploads" / "partners"


def save_partner_image(upload):
    if not upload or not upload.filename:
        return None, None
    original = secure_filename(upload.filename)
    extension = Path(original).suffix.lower().lstrip(".")
    if not original or extension not in ALLOWED_PARTNER_IMAGE_EXTENSIONS:
        return None, "Use a JPG, PNG, or WEBP image for the partner listing."
    expected_format = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[extension]
    try:
        upload.stream.seek(0)
        with Image.open(upload.stream) as image:
            if image.format != expected_format or image.width * image.height > 25_000_000:
                return None, "The uploaded file must be a valid JPG, PNG, or WEBP image under 25 megapixels."
            image.verify()
        upload.stream.seek(0)
    except (UnidentifiedImageError, OSError, ValueError):
        return None, "The uploaded file is not a valid image. Please choose a JPG, PNG, or WEBP image."
    upload_dir = _partner_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"partner-{uuid4().hex}.{extension}"
    upload.save(upload_dir / filename)
    return f"uploads/partners/{filename}", None


def partner_image_url(image_key):
    if not image_key or not image_key.startswith("uploads/partners/"):
        return None
    filename = Path(image_key).name
    if not filename or image_key != f"uploads/partners/{filename}":
        return None
    if not (_partner_upload_dir() / filename).is_file():
        return None
    return f"/static/uploads/partners/{filename}"


def delete_partner_image(image_key):
    if not image_key or not image_key.startswith("uploads/partners/"):
        return
    filename = Path(image_key).name
    if filename and image_key == f"uploads/partners/{filename}":
        path = _partner_upload_dir() / filename
        if path.is_file():
            path.unlink()
