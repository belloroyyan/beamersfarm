"""Render an exact-text, social-preview image for a public shop update."""

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask import current_app

WIDTH, HEIGHT = 1200, 630
BG = "#23382f"
PAPER = "#f5f3eb"
INK = "#263b31"
MUTED = "#6f8178"
LIME = "#c6ba91"
WHITE = "#fffdf8"


def _font(size, bold=False):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def _safe_text(text, font):
    text = str(text or "")
    safe = []
    for char in text:
        try:
            font.getbbox(char)
            safe.append(char)
        except (UnicodeEncodeError, OSError):
            safe.append("?")
    return "".join(safe)


def _wrap(draw, text, font, max_width, max_lines):
    text = re.sub(r"\s+", " ", _safe_text(text, font)).strip()
    if not text:
        return []
    words = text.split(" ")
    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > max_width:
            lines.append(line)
            line = word
            if len(lines) == max_lines:
                break
        else:
            line = candidate
    else:
        if line:
            lines.append(line)
        return lines

    if line and len(lines) < max_lines:
        lines.append(line)
    overflow = len(lines) < len(words) or words and " ".join(lines) != text
    if overflow:
        lines = lines[:max_lines]
        last = lines[-1].rstrip(" .…")
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def _draw_wrapped(draw, lines, xy, font, fill, line_height):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _uploaded_image(update):
    if not update.image or not update.image.startswith("uploads/updates/"):
        return None
    upload_dir = Path(current_app.config["UPDATE_UPLOAD_FOLDER"]).resolve()
    path = (upload_dir / Path(update.image).name).resolve()
    if path.parent != upload_dir or not path.is_file():
        return None
    try:
        with Image.open(path) as source:
            source.seek(0)
            return ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, ValueError):
        return None


def render_update_share_image(update):
    """Return a PNG byte string sized for Open Graph and common social previews."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=30, fill=PAPER)

    panel_box = (812, 42, 1164, 588)
    photo = _uploaded_image(update)
    if photo is not None:
        panel_width = panel_box[2] - panel_box[0]
        panel_height = panel_box[3] - panel_box[1]
        photo = ImageOps.fit(photo, (panel_width, panel_height), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (panel_width, panel_height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel_width, panel_height), radius=24, fill=255)
        image.paste(photo, (panel_box[0], panel_box[1]), mask)
        # A light lower-edge tint keeps the branded image readable without hiding the photo.
        overlay = Image.new("RGBA", (panel_width, 128), (35, 56, 47, 205))
        image.paste(overlay, (panel_box[0], panel_box[3] - 128), overlay)
        draw = ImageDraw.Draw(image)
        draw.text((panel_box[0] + 25, panel_box[3] - 91), "BEAMERS FARM", font=_font(21, True), fill=WHITE)
        draw.text((panel_box[0] + 25, panel_box[3] - 59), "FRESH FROM OSOGBO", font=_font(14, True), fill="#d9e3d7")
    else:
        x1, y1, x2, y2 = panel_box
        draw.rounded_rectangle(panel_box, radius=24, fill=BG)
        center_x, center_y = x1 + 180, y1 + 184
        for radius in (126, 91, 58):
            draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline="#526a4f", width=2)
        for offset in range(0, 310, 28):
            draw.line((x1 + 20, y1 + 90 + offset, x2 - 22, y1 + 90 + offset), fill="#334b3d", width=1)
        draw.ellipse((x1 + 68, y1 + 136, x1 + 285, y1 + 353), outline=LIME, width=3)
        draw.ellipse((x1 + 104, y1 + 172, x1 + 249, y1 + 317), outline="#70845f", width=2)
        draw.text((x1 + 56, y2 - 92), "BEAMERS FARM", font=_font(20, True), fill=WHITE)
        draw.text((x1 + 56, y2 - 61), "FRESH FROM OSOGBO", font=_font(14, True), fill="#d9e3d7")

    logo_path = Path(current_app.static_folder) / "images" / "brand-mark.png"
    try:
        with Image.open(logo_path) as logo_source:
            logo = logo_source.convert("RGBA")
        logo.thumbnail((54, 54), Image.Resampling.LANCZOS)
        image.paste(logo, (78, 63), logo)
    except (OSError, ValueError):
        draw.rounded_rectangle((78, 63, 132, 117), radius=14, fill=BG)
        draw.text((87, 76), "BF", font=_font(24, True), fill=LIME)

    draw.text((148, 68), "BEAMERS FARM", font=_font(20, True), fill=INK)
    draw.text((148, 96), "FRESH, CLEAN, HYGIENICALLY PACKAGED", font=_font(12, True), fill=MUTED)
    draw.rounded_rectangle((78, 145, 222, 176), radius=15, fill="#e7e8d9")
    draw.text((94, 153), "FARM UPDATE", font=_font(13, True), fill=INK)

    date_text = update.created_at.strftime("%d %b %Y") if update.created_at else "Beamers Farm"
    draw.text((244, 151), date_text, font=_font(15), fill=MUTED)

    title_font = _font(45, True)
    title_lines = _wrap(draw, update.topic, title_font, 680, 2)
    if len(title_lines) > 1:
        title_font = _font(40, True)
        title_lines = _wrap(draw, update.topic, title_font, 680, 2)
    _draw_wrapped(draw, title_lines, (78, 204), title_font, INK, 55)

    body_font = _font(23)
    body_text = re.sub(r"\s+", " ", update.body or "").strip()
    if len(body_text) > 320:
        body_text = body_text[:317].rsplit(" ", 1)[0] + "…"
    body_lines = _wrap(draw, body_text, body_font, 680, 5)
    _draw_wrapped(draw, body_lines, (80, 344), body_font, "#53665a", 34)

    draw.line((80, 526, 754, 526), fill="#d5d8cc", width=2)
    draw.text((80, 545), "READ THE FULL UPDATE ON BEAMERS FARM", font=_font(14, True), fill=INK)
    draw.text((80, 568), "Open the shared link for full details", font=_font(13), fill=MUTED)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
