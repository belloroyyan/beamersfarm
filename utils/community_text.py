import re
from urllib.parse import urlsplit

from markupsafe import Markup, escape


_CUSTOM_LINK = re.compile(r"\((https?://[^\s)]+)\)\[([^\]\n]{1,160})\]", re.IGNORECASE)
_TOKEN = re.compile(
    r"https?://[^\s<>\"']+|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<![\w])(?:\+?\d[\d\s().-]{6,}\d)(?![\w])",
    re.IGNORECASE,
)
_TRAILING_URL_PUNCTUATION = ".,!?;:)]}"


def _safe_web_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password
    except ValueError:
        return False


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
