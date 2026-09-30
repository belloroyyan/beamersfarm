import hashlib
import hmac

from flask import Blueprint, abort, current_app, jsonify, request

from models import OrderNotification, db

whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/webhooks/whatsapp")


@whatsapp_bp.get("")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token and hmac.compare_digest(token, current_app.config["WHATSAPP_VERIFY_TOKEN"]):
        return challenge or "", 200
    abort(403)


@whatsapp_bp.post("")
def receive_webhook():
    app_secret = current_app.config["META_APP_SECRET"]
    signature = request.headers.get("X-Hub-Signature-256", "")
    raw_body = request.get_data()
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not app_secret or not hmac.compare_digest(signature, expected):
        abort(403)

    payload = request.get_json(silent=True) or {}
    updated = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status_event in value.get("statuses", []):
                message_id = status_event.get("id")
                status = status_event.get("status")
                mapped_status = {
                    "sent": "sent",
                    "delivered": "delivered",
                    "read": "read",
                    "failed": "failed",
                }.get(status)
                if not message_id or not mapped_status:
                    continue
                notification = OrderNotification.query.filter_by(
                    provider_message_id=message_id
                ).first()
                if not notification:
                    continue
                status_rank = {"sent": 1, "delivered": 2, "read": 3, "failed": 99}
                if notification.status == "failed" or (
                    notification.status in status_rank
                    and status_rank[mapped_status] < status_rank[notification.status]
                ):
                    continue
                notification.status = mapped_status
                if mapped_status == "failed":
                    errors = status_event.get("errors") or []
                    notification.last_error = str(errors)[:2000]
                db.session.commit()
                updated += 1
    return jsonify(status="accepted", updated=updated), 200
