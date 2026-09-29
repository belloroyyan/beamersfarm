import hmac
import secrets
from urllib.parse import urljoin, urlparse

from flask import abort, request, session


CSRF_SESSION_KEY = "_csrf_token"


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    expected = session.get(CSRF_SESSION_KEY)
    supplied = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400, description="The form expired. Please refresh and try again.")


def is_safe_redirect_url(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    target_url = urlparse(urljoin(request.host_url, target))
    return target_url.scheme in {"http", "https"} and target_url.netloc == host_url.netloc
