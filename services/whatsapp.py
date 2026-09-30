"""Small, dependency-free Meta WhatsApp Cloud API client."""

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import and_, or_, update

from models import OrderNotification, db


def _graph_url():
    version = current_app.config["WHATSAPP_GRAPH_API_VERSION"]
    phone_number_id = current_app.config["WHATSAPP_PHONE_NUMBER_ID"]
    return f"https://graph.facebook.com/{version}/{phone_number_id}/messages"


def _template_payload(notification):
    order = notification.order
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": notification.recipient,
        "type": "template",
        "template": {
            "name": current_app.config["WHATSAPP_TEMPLATE_NAME"],
            "language": {"code": current_app.config["WHATSAPP_TEMPLATE_LANGUAGE"]},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": order.customer_name},
                        {"type": "text", "text": f"{order.id:04d}"},
                        {"type": "text", "text": f"{order.total:,.2f}"},
                    ],
                }
            ],
        },
    }


def send_notification(notification):
    """Send one notification and return Meta's accepted message ID.

    This function is only called by the scheduled processor when explicitly
    enabled. It never exposes the access token in an exception or log.
    """
    token = current_app.config["WHATSAPP_ACCESS_TOKEN"]
    if not current_app.config["WHATSAPP_ENABLED"]:
        raise RuntimeError("WhatsApp sending is disabled")
    if not token or not current_app.config["WHATSAPP_PHONE_NUMBER_ID"]:
        raise RuntimeError("WhatsApp sender credentials are incomplete")

    body = json.dumps(_template_payload(notification)).encode("utf-8")
    request = urllib.request.Request(
        _graph_url(),
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Meta API HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Meta API connection failed: {exc}") from exc

    messages = payload.get("messages") or []
    if not messages or not messages[0].get("id"):
        raise RuntimeError("Meta API response did not include a message ID")
    return messages[0]["id"]


def process_pending_notifications(limit=20):
    """Process a bounded batch; safe to invoke from a Railway cron service."""
    if not current_app.config["WHATSAPP_ENABLED"]:
        return {"processed": 0, "sent": 0, "failed": 0, "disabled": True}

    now = datetime.utcnow()
    stale_before = now - timedelta(minutes=10)
    candidate_ids = (
        OrderNotification.query.filter(
            OrderNotification.channel == "whatsapp",
            OrderNotification.status.in_(["pending", "processing"]),
            (OrderNotification.next_attempt_at.is_(None) | (OrderNotification.next_attempt_at <= now)),
            (
                (OrderNotification.status == "pending")
                | OrderNotification.processing_started_at.is_(None)
                | (OrderNotification.processing_started_at <= stale_before)
            ),
        )
        .order_by(OrderNotification.created_at.asc())
        .limit(limit)
        .with_entities(OrderNotification.id)
        .all()
    )
    results = {"processed": 0, "sent": 0, "failed": 0, "disabled": False}
    for (notification_id,) in candidate_ids:
        claim = db.session.execute(
            update(OrderNotification)
            .where(
                OrderNotification.id == notification_id,
                OrderNotification.channel == "whatsapp",
                (OrderNotification.next_attempt_at.is_(None) | (OrderNotification.next_attempt_at <= now)),
                or_(
                    OrderNotification.status == "pending",
                    and_(
                        OrderNotification.status == "processing",
                        or_(
                            OrderNotification.processing_started_at.is_(None),
                            OrderNotification.processing_started_at <= stale_before,
                        ),
                    ),
                ),
            )
            .values(
                status="processing",
                processing_started_at=now,
                attempts=OrderNotification.attempts + 1,
            )
        )
        db.session.commit()
        if claim.rowcount != 1:
            continue
        notification = db.session.get(OrderNotification, notification_id)
        if not notification:
            continue
        results["processed"] += 1
        try:
            provider_id = send_notification(notification)
            notification.status = "sent"
            notification.provider_message_id = provider_id
            notification.sent_at = datetime.utcnow()
            notification.processing_started_at = None
            notification.last_error = None
            db.session.commit()
            results["sent"] += 1
        except Exception as exc:  # noqa: BLE001 - persist safe operational failure
            notification.processing_started_at = None
            notification.last_error = str(exc)[:2000]
            if notification.attempts >= current_app.config["WHATSAPP_MAX_ATTEMPTS"]:
                notification.status = "failed"
                results["failed"] += 1
            else:
                notification.status = "pending"
                delay = min(60 * (2 ** max(notification.attempts - 1, 0)), 3600)
                notification.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)
            db.session.commit()
    return results
