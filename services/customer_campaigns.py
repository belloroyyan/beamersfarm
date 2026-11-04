"""Isolated, consent-aware delivery for one-off customer campaigns."""

import hashlib
import hmac
import json
import re
import urllib.error
import urllib.request

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from models import CustomerPushSubscription
from services.email import send_email, smtp_is_configured
from utils.notifications import normalize_nigerian_phone
from utils.web_push import _send_to_subscriptions, web_push_is_configured


_CHANNELS = ("push", "whatsapp", "email")
_MIME_TOKEN = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+$")


def _whatsapp_is_ready():
    return bool(
        current_app.config.get("WHATSAPP_ENABLED")
        and current_app.config.get("WHATSAPP_PHONE_NUMBER_ID")
        and current_app.config.get("WHATSAPP_ACCESS_TOKEN")
        and current_app.config.get("WHATSAPP_GRAPH_API_VERSION")
        and current_app.config.get("WHATSAPP_CAMPAIGN_TEMPLATE_NAME")
        and current_app.config.get("WHATSAPP_CAMPAIGN_TEMPLATE_LANGUAGE")
    )


def campaign_channel_readiness():
    """Return safe configuration readiness details for each campaign channel."""
    whatsapp_ready = _whatsapp_is_ready()
    email_ready = smtp_is_configured()
    push_ready = web_push_is_configured()
    return {
        "push": {
            "ready": push_ready,
            "reason": None if push_ready else "VAPID public key, private key, and subject must be configured.",
        },
        "whatsapp": {
            "ready": whatsapp_ready,
            "reason": None if whatsapp_ready else "Enable Meta WhatsApp, supply the phone-number ID/access token, and configure an approved campaign template with one body-text placeholder.",
        },
        "email": {
            "ready": email_ready,
            "reason": None if email_ready else "RESEND_API_KEY and RESEND_FROM must be configured.",
        },
    }


def _result(channel, recipient="", status="skipped", provider_message_id=None, error=None):
    return {
        "channel": channel,
        "recipient": recipient,
        "status": status,
        "provider_message_id": provider_message_id,
        "error": error,
    }


def _customer_push_key(customer):
    normalized = normalize_nigerian_phone(customer.phone) or " ".join((customer.phone or "").split()).casefold()
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    return hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def _campaign_root_url():
    # A relative root is valid for the existing service worker when no public origin is configured.
    return current_app.config.get("PUBLIC_ORIGIN", "").rstrip("/") or "/"


def _safe_provider_error(raw_error, *, recipient, title, body, token):
    """Keep useful provider/window diagnostics while stripping message and account data."""
    text = str(raw_error or "WhatsApp provider rejected the message.")
    for sensitive in (token, recipient, title, body):
        if sensitive:
            text = re.sub(re.escape(str(sensitive)), "[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", text, flags=re.IGNORECASE)
    return text[:700]


def _graph_error_text(payload, http_status):
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return f"Meta API HTTP {http_status}."
    pieces = [f"Meta API HTTP {http_status}"]
    code = error.get("code")
    subcode = error.get("error_subcode")
    if code is not None:
        pieces.append(f"code {code}")
    if subcode is not None:
        pieces.append(f"subcode {subcode}")
    # The Graph API's message commonly explains the 24-hour window restriction.
    message = error.get("message") or error.get("error_user_msg") or error.get("error_user_title")
    if message:
        pieces.append(str(message))
    return ": ".join(pieces)


def _send_whatsapp(recipient, title, body):
    token = current_app.config["WHATSAPP_ACCESS_TOKEN"]
    version = current_app.config["WHATSAPP_GRAPH_API_VERSION"]
    phone_number_id = current_app.config["WHATSAPP_PHONE_NUMBER_ID"]
    text = f"{title.strip()}\n\n{body.strip()}" if title.strip() else body.strip()
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": current_app.config["WHATSAPP_CAMPAIGN_TEMPLATE_NAME"],
            "language": {"code": current_app.config["WHATSAPP_CAMPAIGN_TEMPLATE_LANGUAGE"]},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": text}]}],
        },
    }
    request = urllib.request.Request(
        f"https://graph.facebook.com/{version}/{phone_number_id}/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (ValueError, UnicodeDecodeError):
            error_payload = {}
        raise RuntimeError(_safe_provider_error(
            _graph_error_text(error_payload, exc.code),
            recipient=recipient, title=title, body=body, token=token,
        )) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("WhatsApp provider connection failed.") from None
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError("WhatsApp provider returned an invalid response.") from None

    messages = response_payload.get("messages") if isinstance(response_payload, dict) else None
    message_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
    if not message_id:
        raise RuntimeError("WhatsApp provider accepted no message ID; delivery is unconfirmed.")
    return message_id


def _validated_attachments(attachments):
    if attachments is None:
        return []
    if not isinstance(attachments, (list, tuple)):
        raise ValueError("Attachments must be a list of (filename, MIME type, bytes) items.")
    safe_items = []
    for item in attachments:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError("Each attachment must contain a filename, MIME type, and bytes.")
        filename, content_type, data = item
        safe_name = secure_filename(str(filename or "")) or "attachment"
        mime = str(content_type or "application/octet-stream").strip()
        major, separator, minor = mime.partition("/")
        if not separator or not _MIME_TOKEN.fullmatch(major) or not _MIME_TOKEN.fullmatch(minor):
            mime = "application/octet-stream"
        if not isinstance(data, bytes):
            raise ValueError("Attachment content must be bytes.")
        safe_items.append((safe_name, mime, data))
    return safe_items


def _deliver_push(customer, title, body):
    if not customer.push_notifications_enabled:
        return _result("push", "customer push subscriptions", status="skipped", error="Push notifications are disabled in customer preferences.")
    if not web_push_is_configured():
        return _result("push", "customer push subscriptions", error="Web Push is not configured.")
    try:
        subscriptions = CustomerPushSubscription.query.filter_by(
            customer_key=_customer_push_key(customer)
        ).order_by(CustomerPushSubscription.id.asc()).all()
    except SQLAlchemyError:
        from models import db
        db.session.rollback()
        return _result("push", "customer push subscriptions", error="Could not load customer push subscriptions.")
    if not subscriptions:
        return _result("push", "customer push subscriptions", status="skipped", error="No push subscriptions are registered.")
    try:
        delivery = _send_to_subscriptions(subscriptions, title, body, _campaign_root_url(), "customer")
    except Exception:
        return _result("push", f"{len(subscriptions)} customer push subscription(s)", "failed", error="Web Push delivery failed.")
    total, sent, failed = delivery.get("total", len(subscriptions)), delivery.get("sent", 0), delivery.get("failed", 0)
    recipient = f"{total} customer push subscription(s)"
    if sent == total and total > 0:
        return _result("push", recipient, "sent")
    if sent:
        return _result("push", recipient, "failed", error=f"Push delivered to {sent} of {total} subscriptions; {failed} failed or expired.")
    return _result("push", recipient, "failed", error=f"Push delivery failed for {total} subscription(s).")


def deliver_customer_campaign(customer, channels, title, body, attachments=None):
    """Deliver a campaign over requested channels, returning exactly one outcome per channel."""
    requested = []
    for channel in channels or ():
        normalized = str(channel).strip().lower()
        if normalized not in requested:
            requested.append(normalized)
    results = []
    if not customer or not getattr(customer, "active", False) or getattr(customer, "deleted_at", None):
        return [_result(channel, status="skipped", error="Customer account is inactive.") for channel in requested]

    campaign_title = str(title or "").strip()
    campaign_body = str(body or "").strip()
    for channel in requested:
        if channel not in _CHANNELS:
            results.append(_result(channel, status="skipped", error="Unsupported campaign channel."))
            continue
        if not campaign_body:
            results.append(_result(channel, status="failed", error="Campaign message body is empty."))
            continue

        if channel == "push":
            results.append(_deliver_push(
                customer,
                campaign_title or "A message from Beamers Farms",
                campaign_body,
            ))
            continue

        if channel == "whatsapp":
            recipient = normalize_nigerian_phone(getattr(customer, "phone", ""))
            if not customer.whatsapp_notifications_enabled:
                results.append(_result(channel, recipient, status="skipped", error="WhatsApp campaign consent is not enabled."))
            elif not recipient:
                results.append(_result(channel, status="skipped", error="Customer phone number is missing or invalid."))
            elif not _whatsapp_is_ready():
                results.append(_result(channel, recipient, status="skipped", error="WhatsApp sending is disabled or provider credentials are incomplete."))
            else:
                try:
                    if len((f"{campaign_title}\n\n" if campaign_title else "") + campaign_body) > 1024:
                        results.append(_result(channel, recipient, "failed", error="WhatsApp template text exceeds Meta's 1,024-character parameter limit."))
                        continue
                    provider_id = _send_whatsapp(recipient, campaign_title, campaign_body)
                    results.append(_result(channel, recipient, "sent", provider_id))
                except Exception as exc:
                    results.append(_result(channel, recipient, "failed", error=str(exc)[:700]))
            continue

        recipient = (getattr(customer, "email", None) or "").strip()
        if not customer.email_verified:
            results.append(_result(channel, recipient, status="skipped", error="Customer email address is not verified."))
        elif not recipient:
            results.append(_result(channel, status="skipped", error="Customer email address is missing."))
        elif not smtp_is_configured():
            results.append(_result(channel, recipient, status="skipped", error="Resend email delivery is not configured."))
        elif len(campaign_title) > 180:
            results.append(_result(channel, recipient, "failed", error="Email subject exceeds the sender limit."))
        else:
            try:
                safe_attachments = _validated_attachments(attachments)
                subject = campaign_title or "A message from Beamers Farms"
                send_email(recipient, subject, campaign_body, safe_attachments)
                results.append(_result(channel, recipient, "sent"))
            except Exception as exc:
                # The Resend helper returns generic transport errors; never log message or attachment content.
                results.append(_result(channel, recipient, "failed", error=str(exc)[:500]))
    return results
