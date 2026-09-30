"""Helpers for owner updates: image uploads and clickable links/emails/phones."""

import re
from pathlib import Path
from uuid import uuid4

from flask import current_app
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename

ALLOWED_UPDATE_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

_TOKEN = re.compile(
    r"(?P<url>(?:https?://|www\.)[^\s<>\"']+[^\s<>\"'.,;:!?)\]])"
    r"|(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    r"|(?P<phone>\+?\d[\d\s-]{8,16}\d)"
)


def linkify(text):
    """Escape text, then turn URLs, emails and phone numbers into links. Keeps line breaks."""
    out = []
    last = 0
    text = text or ""
    for m in _TOKEN.finditer(text):
        out.append(escape(text[last:m.start()]))
        value = m.group(0)
        if m.group("url"):
            href = value if value.startswith("http") else "https://" + value
            out.append(Markup('<a href="{}" target="_blank" rel="noopener nofollow">{}</a>').format(href, value))
        elif m.group("email"):
            out.append(Markup('<a href="mailto:{}">{}</a>').format(value, value))
        else:
            digits = re.sub(r"[^\d+]", "", value)
            out.append(Markup('<a href="tel:{}">{}</a>').format(digits, value))
        last = m.end()
    out.append(escape(text[last:]))
    return Markup("<br>").join(Markup("").join(out).split("\n"))


def update_image_url(image_key):
    if not image_key:
        return None
    if not (Path(current_app.config["UPDATE_UPLOAD_FOLDER"]) / Path(image_key).name).is_file():
        return None
    return "/static/" + image_key


def save_update_image(upload):
    if not upload or not upload.filename:
        return None, None
    original = secure_filename(upload.filename)
    extension = Path(original).suffix.lower().lstrip(".")
    if not original or extension not in ALLOWED_UPDATE_IMAGE_EXTENSIONS:
        return None, "Use a JPG, PNG, WEBP or GIF image."
    upload_dir = Path(current_app.config["UPDATE_UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"update-{uuid4().hex}.{extension}"
    upload.save(upload_dir / filename)
    return f"uploads/updates/{filename}", None


def delete_update_image(image_key):
    if image_key:
        path = Path(current_app.config["UPDATE_UPLOAD_FOLDER"]) / Path(image_key).name
        if path.is_file():
            path.unlink()
