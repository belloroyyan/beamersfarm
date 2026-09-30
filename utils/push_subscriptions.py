import hashlib
import ipaddress
import re
from urllib.parse import urlsplit

from flask import jsonify, session

from models import StaffPushSubscription, db
from utils.web_push import web_push_is_configured


STAFF_ROLES = {"owner", "dispatch_rider"}


def valid_push_endpoint(endpoint):
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 2048:
        return False
    try:
        parsed = urlsplit(endpoint)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password or port not in (None, 443):
        return False
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            return False
    return True


def save_staff_push_subscription(staff_role):
    if staff_role not in STAFF_ROLES:
        return jsonify(error="Unsupported staff role."), 403
    if not web_push_is_configured():
        return jsonify(error="Push notifications are not configured by the site owner."), 503
    payload = request_json_object()
    endpoint = payload.get("endpoint")
    keys = payload.get("keys")
    p256dh = keys.get("p256dh") if isinstance(keys, dict) else None
    auth = keys.get("auth") if isinstance(keys, dict) else None
    if (
        not valid_push_endpoint(endpoint)
        or not isinstance(p256dh, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{40,200}", p256dh)
        or not isinstance(auth, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{16,200}", auth)
    ):
        return jsonify(error="The browser returned an invalid push subscription."), 400

    endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    subscription = StaffPushSubscription.query.filter_by(
        staff_role=staff_role, endpoint_hash=endpoint_hash
    ).first()
    if subscription is None:
        subscription = StaffPushSubscription(
            staff_role=staff_role,
            endpoint_hash=endpoint_hash,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        db.session.add(subscription)
    else:
        subscription.endpoint = endpoint
        subscription.p256dh = p256dh
        subscription.auth = auth
    db.session.commit()
    session["staff_push_subscription_hash"] = endpoint_hash
    return jsonify(message="Push notifications enabled for this device."), 201


def delete_staff_push_subscription(staff_role):
    if staff_role not in STAFF_ROLES:
        return jsonify(error="Unsupported staff role."), 403
    payload = request_json_object()
    endpoint = payload.get("endpoint")
    if not valid_push_endpoint(endpoint):
        return jsonify(error="The browser returned an invalid push subscription."), 400
    endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    subscription = StaffPushSubscription.query.filter_by(
        staff_role=staff_role, endpoint_hash=endpoint_hash
    ).first()
    if subscription is not None:
        db.session.delete(subscription)
        db.session.commit()
    if session.get("staff_push_subscription_hash") == endpoint_hash:
        session.pop("staff_push_subscription_hash", None)
    return jsonify(message="Push notifications disabled for this device."), 200


def request_json_object():
    from flask import request

    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}
