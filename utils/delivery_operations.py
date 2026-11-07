"""Delivery hours, automatic shop scheduling, batch closure and customer recovery notices."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import current_app, url_for
from models import DeliveryRedeliveryRequest, DispatchBatch, Order, OrderNotification, ShopSettings, db
from services.email import send_email
from utils.notifications import normalize_nigerian_phone
from utils.web_push import send_customer_order_confirmed_push

TZ = ZoneInfo("Africa/Lagos")
DONE = {"Delivered", "Picked up", "Cancelled"}

def _settings():
    return ShopSettings.query.get(1)

def _channels(settings):
    try:
        values = json.loads(settings.closure_channels_json or "[]")
    except (TypeError, ValueError):
        values = []
    return [v for v in values if v in {"push", "whatsapp", "email"}]

def delivery_windows(settings=None):
    settings = settings or _settings()
    try:
        values = json.loads(settings.delivery_windows_json or "[]")
    except (TypeError, ValueError):
        values = []
    return [str(v).strip() for v in values if str(v).strip()][:12]

def _local_now():
    return datetime.now(TZ)

def _is_inside(now, opening, closing):
    try:
        oh, om = [int(v) for v in (opening or "07:00").split(":")]
        ch, cm = [int(v) for v in (closing or "19:00").split(":")]
    except (TypeError, ValueError):
        oh, om, ch, cm = 7, 0, 19, 0
    start = now.replace(hour=oh, minute=om, second=0, microsecond=0)
    end = now.replace(hour=ch, minute=cm, second=0, microsecond=0)
    return start <= now < end

def _public_redelivery_url(order):
    try:
        return url_for("shop.redelivery_request", order_ref=order.public_id, token=order.public_token, _external=True)
    except RuntimeError:
        return f"/request-redelivery/{order.public_id}/{order.public_token}"

def _closure_text(order):
    link = _public_redelivery_url(order)
    return ("Your Beamers Farms delivery could not leave today because the delivery window has closed. "
            f"Please request another delivery here: {link} or choose farm pickup from the farm.")

def _notify_closed_order(order, channels):
    body = _closure_text(order)
    title = "Delivery closed for today"
    customer = order.customer if getattr(order, "customer", None) and order.customer.active else None
    for channel in channels:
        if OrderNotification.query.filter_by(order_id=order.id, channel=channel, event="delivery_closed").first():
            continue
        recipient = (order.email or "") if channel == "email" else normalize_nigerian_phone(order.phone) or order.phone
        notification = OrderNotification(order_id=order.id, channel=channel, event="delivery_closed", recipient=recipient or "", message=body, status="pending")
        db.session.add(notification)
        db.session.flush()
        try:
            if channel == "push":
                result = send_customer_order_confirmed_push(order)
                notification.status = "sent" if result.get("sent") else "skipped"
                notification.last_error = None if result.get("sent") else "No active customer push subscription."
            elif channel == "email":
                if not order.email:
                    notification.status, notification.last_error = "skipped", "Order has no email address."
                else:
                    send_email(order.email, title, body)
                    notification.status = "sent"
            elif channel == "whatsapp":
                if not order.whatsapp_opt_in or not recipient:
                    notification.status, notification.last_error = "skipped", "WhatsApp consent or phone number is unavailable."
                else:
                    # Keep WhatsApp delivery in the existing retryable notification queue.
                    notification.status = "pending"
            if notification.status == "sent":
                notification.sent_at = datetime.utcnow()
        except Exception as exc:
            notification.status, notification.last_error = "failed", str(exc)[:500]
    return body

def close_expired_batches(now=None, close_today=False):
    """Close unfinished batches whose delivery window has passed, or all batches for a day that has closed."""
    settings = _settings()
    if not settings:
        return 0
    now_local = now or _local_now()
    now_utc = now_local.astimezone(timezone.utc).replace(tzinfo=None)
    batches = DispatchBatch.query.filter(DispatchBatch.status == "open", DispatchBatch.window_end <= now_utc).all()
    if close_today:
        batches = [batch for batch in DispatchBatch.query.filter(DispatchBatch.status == "open").all()
                   if batch.window_start.replace(tzinfo=timezone.utc).astimezone(TZ).date() <= now_local.date()]
    changed = 0
    channels = _channels(settings)
    for batch in batches:
        batch.status = "closed"
        batch.closed_at = datetime.utcnow()
        changed += 1
        for order in list(batch.orders or []):
            if order.status not in DONE:
                _notify_closed_order(order, channels)
    if changed:
        db.session.commit()
    return changed

def sync_delivery_schedule():
    """Synchronise shop hours and close expired delivery batches on every request.

    Manual shop closure is authoritative even when automatic shop hours are disabled.
    Window expiry is evaluated independently so an unfinished batch cannot remain open
    merely because the shop is still accepting orders.
    """
    settings = _settings()
    if not settings:
        return
    now = _local_now()
    was_open = bool(settings.is_open)
    if settings.auto_shop_hours:
        target = _is_inside(now, settings.delivery_open_time, settings.delivery_close_time)
        if was_open != target:
            settings.is_open = target
            settings.updated_at = datetime.utcnow()
            db.session.commit()
    # Close all batches when the shop is closed; otherwise close only elapsed windows.
    if not settings.is_open:
        close_expired_batches(now, close_today=True)
    else:
        close_expired_batches(now, close_today=False)
