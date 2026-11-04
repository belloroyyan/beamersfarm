import re
from urllib.parse import unquote, urlsplit

from flask import current_app
from werkzeug.routing import RequestRedirect
from markupsafe import Markup, escape


_CUSTOM_LINK = re.compile(r"\((https?://[^\s)]+)\)\[([^\]\n]{1,160})\]", re.IGNORECASE)
_TOKEN = re.compile(
    r"https?://[^\s<>\"']+|(?<![\w/:])/(?!/)[^\s<>\"']+|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<![\w])(?:\+?\d[\d\s().-]{6,}\d)(?![\w])",
    re.IGNORECASE,
)
_TRAILING_URL_PUNCTUATION = ".,!?;:)]}"
_PUBLIC_INTERNAL_ENDPOINTS = {
    "shop.index", "shop.products", "shop.product_detail", "shop.updates",
    "shop.update_detail", "shop.help_page", "shop.gallery", "shop.privacy",
    "shop.wholesale", "shop.track_order", "shop.cart", "shop.partner_offer",
    "community.feed", "community.post_redirect", "reviews.submit_review",
    "reviews.testimonials", "complaints.create_complaint",
}


def _safe_web_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password
    except ValueError:
        return False


def safe_internal_path(value):
    """Return a safe local URL only when it matches an explicitly public GET route."""
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return None
    if "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        decoded_value = unquote(value)
        decoded_path = unquote(parsed.path)
    except (ValueError, UnicodeError):
        return None
    if parsed.scheme or parsed.netloc or parsed.username or parsed.password:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in decoded_value):
        return None
    if "\\" in decoded_path or "//" in parsed.path or re.search(r"%(?:2f|5c)", parsed.path, re.IGNORECASE):
        return None
    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        return None
    adapter = current_app.url_map.bind("localhost")
    try:
        endpoint, _values = adapter.match(parsed.path, method="GET")
    except RequestRedirect as redirect:
        try:
            endpoint, _values = adapter.match(urlsplit(redirect.new_url).path, method="GET")
        except Exception:
            return None
    except Exception:
        return None
    if endpoint not in _PUBLIC_INTERNAL_ENDPOINTS:
        return None
    return value


def community_linkify(value):
    """Return escaped community text with only safe, clickable contact links."""
    text = str(value or "")
    output = []
    cursor = 0
    for match in _TOKEN.finditer(text):
        output.append(escape(text[cursor:match.start()]))
        token = match.group(0)
        if token.startswith("("):
            # A custom named-link token is parsed separately below; this is defensive.
            output.append(escape(token))
        elif token.lower().startswith(("http://", "https://")):
            url = token
            suffix = ""
            while url and url[-1] in _TRAILING_URL_PUNCTUATION:
                suffix = url[-1] + suffix
                url = url[:-1]
            if _safe_web_url(url):
                safe_url = escape(url)
                output.append(Markup('<a href="{}" target="_blank" rel="nofollow noopener noreferrer">{}</a>').format(safe_url, escape(url)))
                output.append(escape(suffix))
            else:
                output.append(escape(token))
        elif token.startswith("/"):
            path = token
            suffix = ""
            while path and path[-1] in _TRAILING_URL_PUNCTUATION:
                suffix = path[-1] + suffix
                path = path[:-1]
            safe_path = safe_internal_path(path)
            if safe_path:
                output.append(Markup('<a href="{}">{}</a>').format(escape(safe_path), escape(path)))
                output.append(escape(suffix))
            else:
                output.append(escape(token))
        elif "@" in token:
            output.append(Markup('<a href="mailto:{}">{}</a>').format(escape(token), escape(token)))
        else:
            digits = re.sub(r"\D", "", token)
            if 8 <= len(digits) <= 15:
                output.append(Markup('<a href="tel:{}">{}</a>').format(escape("+" + digits if token.strip().startswith("+") else digits), escape(token)))
            else:
                output.append(escape(token))
        cursor = match.end()
    output.append(escape(text[cursor:]))
    linked = Markup("").join(output)

    # Render explicit links after the plain-token pass, escaping both label and target.
    # Placeholders avoid reparsing generated anchor markup or double-linking its URL.
    placeholders = []
    def replace_custom(match):
        url, label = match.groups()
        if not _safe_web_url(url):
            return match.group(0)
        placeholder = f"\x00BF_LINK_{len(placeholders)}\x00"
        placeholders.append(Markup('<a href="{}" target="_blank" rel="nofollow noopener noreferrer">{}</a>').format(escape(url), escape(label)))
        return placeholder

    custom_text = _CUSTOM_LINK.sub(replace_custom, text)
    if placeholders:
        # Re-run the safe tokenizer on the custom-link source, then replace only literal tokens.
        linked_parts = []
        cursor = 0
        for match in re.finditer(r"\x00BF_LINK_(\d+)\x00", custom_text):
            linked_parts.append(community_linkify(custom_text[cursor:match.start()]) if custom_text[cursor:match.start()] else Markup(""))
            linked_parts.append(placeholders[int(match.group(1))])
            cursor = match.end()
        linked_parts.append(community_linkify(custom_text[cursor:]) if custom_text[cursor:] else Markup(""))
        return Markup("").join(linked_parts)
    return linked
