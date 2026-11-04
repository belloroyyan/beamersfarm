"""Resend email delivery for customer verification and owner messaging."""
import base64
import json
import urllib.error
import urllib.request
from email.utils import parseaddr
from flask import current_app

def resend_is_configured():
    return bool(current_app.config.get("RESEND_API_KEY") and current_app.config.get("RESEND_FROM"))

# Backwards-compatible name used by customer and campaign routes.
def smtp_is_configured():
    return resend_is_configured()

def send_email(recipient, subject, body, attachments=None):
    if not resend_is_configured():
        raise RuntimeError("Email sending is not configured. Add RESEND_API_KEY and RESEND_FROM.")
    recipient = (recipient or "").strip()
    sender = current_app.config["RESEND_FROM"].strip()
    if not recipient or "@" not in recipient or not parseaddr(sender)[1] or "@" not in parseaddr(sender)[1]:
        raise RuntimeError("The sender or recipient email address is invalid.")
    subject = (subject or "").strip(); body = (body or "").strip()
    if len(subject) > 180 or not body:
        raise RuntimeError("Email subject or message body is invalid.")
    payload = {"from": sender, "to": [recipient], "subject": subject, "text": body}
    safe_attachments = []
    for filename, content_type, data in attachments or []:
        if not isinstance(data, bytes):
            raise RuntimeError("Email attachment content is invalid.")
        safe_attachments.append({"filename": filename, "content": base64.b64encode(data).decode("ascii")})
    if safe_attachments:
        payload["attachments"] = safe_attachments
    request = urllib.request.Request(
        "https://api.resend.com/emails", data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {current_app.config['RESEND_API_KEY']}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try: details = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception: details = {}
        message = details.get("message") or "Resend rejected the email."
        raise RuntimeError(f"Resend email delivery failed: {message}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError("Resend email delivery failed. Check API access and sender configuration.") from None
    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError("Resend returned no email ID; delivery is unconfirmed.")
    return result["id"]
