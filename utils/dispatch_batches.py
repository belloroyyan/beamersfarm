from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from flask import current_app
from models import DispatchBatch, ShopSettings, db

SHOP_TZ = ZoneInfo("Africa/Lagos")
# Orders in these states no longer need an estimate (already moving, finished, or void).
NO_ESTIMATE_STATUSES = {"Out for delivery", "Delivered", "Picked up", "Cancelled", "Ready for pickup"}

def order_weight(order):
    total=Decimal("0.000")
    for item in order.items:
        total += Decimal(str(item.requested_weight_kg or item.quantity or 0))
    return max(total, Decimal("0.001"))

def assign_dispatch_batch(order):
    if order.fulfillment_type != "delivery": return None
    settings=ShopSettings.query.get(1)
    hours=max(Decimal("0.25"), Decimal(str(settings.dispatch_batch_hours if settings else 2)))
    limit=max(Decimal("0.001"), Decimal(str(settings.dispatch_batch_weight_limit if settings else 50)))
    now=datetime.utcnow(); seconds=float(hours)*3600; epoch=datetime(2000,1,1); elapsed=(now-epoch).total_seconds(); start=epoch+timedelta(seconds=(elapsed//seconds)*seconds); end=start+timedelta(seconds=seconds)
    weight=order_weight(order)
    batch=DispatchBatch.query.filter_by(window_start=start,status="open").order_by(DispatchBatch.id.desc()).first()
    if not batch or Decimal(str(batch.assigned_weight or 0))+weight>limit:
        batch=DispatchBatch(window_start=start,window_end=end,weight_limit=limit,assigned_weight=Decimal("0.000"),status="open"); db.session.add(batch); db.session.flush()
    batch.assigned_weight=Decimal(str(batch.assigned_weight or 0))+weight
    order.dispatch_batch_id=batch.id
    return batch


def _hours():
    cfg = current_app.config
    return int(cfg.get("SHOP_OPEN_HOUR", 7)), int(cfg.get("SHOP_CLOSE_HOUR", 19))

def _in_hours(moment, open_hour, close_hour):
    """Move a local time forward to the next moment the shop is open."""
    opening = moment.replace(hour=open_hour, minute=0, second=0, microsecond=0)
    closing = moment.replace(hour=close_hour, minute=0, second=0, microsecond=0)
    if moment < opening:
        return opening
    if moment >= closing:
        return opening + timedelta(days=1)
    return moment

def _add_open_time(moment, delta, open_hour, close_hour):
    """Add transit time, counting only minutes inside opening hours."""
    moment = _in_hours(moment, open_hour, close_hour)
    remaining = delta
    while True:
        closing = moment.replace(hour=close_hour, minute=0, second=0, microsecond=0)
        available = closing - moment
        if remaining <= available:
            return moment + remaining
        remaining -= available
        moment = _in_hours(closing, open_hour, close_hour)

def _clock(moment):
    return moment.strftime("%I:%M %p").lstrip("0")

def _day_word(moment, today):
    gap = (moment.date() - today.date()).days
    if gap == 0:
        return "today"
    if gap == 1:
        return "tomorrow"
    return moment.strftime("%A %d %b")

def delivery_estimate(order, now=None):
    """Customer-facing delivery window derived from the order's dispatch batch.

    The batch closes at ``window_end`` and the rider leaves then. If that moment has
    already passed (for example payment was verified late) the estimate counts from
    now instead. Returns None when no estimate applies.
    """
    batch = getattr(order, "dispatch_batch", None)
    if order is None or order.fulfillment_type != "delivery" or batch is None:
        return None
    if order.status in NO_ESTIMATE_STATUSES:
        return None
    open_hour, close_hour = _hours()
    now_utc = (now or datetime.utcnow()).replace(tzinfo=timezone.utc)
    close_utc = batch.window_end.replace(tzinfo=timezone.utc)
    dispatch_local = max(now_utc, close_utc).astimezone(SHOP_TZ)
    dispatch_local = _in_hours(dispatch_local, open_hour, close_hour)
    cfg = current_app.config
    low = max(5, int(cfg.get("DELIVERY_TRANSIT_MIN_MINUTES", 30)))
    high = max(low, int(cfg.get("DELIVERY_TRANSIT_MAX_MINUTES", 90)))
    start = _add_open_time(dispatch_local, timedelta(minutes=low), open_hour, close_hour)
    end = _add_open_time(dispatch_local, timedelta(minutes=high), open_hour, close_hour)
    closing = dispatch_local.replace(hour=close_hour, minute=0, second=0, microsecond=0)
    if start >= closing:
        # Earliest arrival would fall after closing: quote the next morning instead.
        morning = _in_hours(closing, open_hour, close_hour)
        start = morning + timedelta(minutes=low)
        end = morning + timedelta(minutes=high)
        dispatch_local = morning
    elif end > closing:
        end = closing  # deliveries finish by closing time
    today = now_utc.astimezone(SHOP_TZ)
    if start.date() == end.date():
        text = f"{_day_word(start, today)}, {_clock(start)} – {_clock(end)}"
    else:
        text = f"{_day_word(start, today)} {_clock(start)} – {_day_word(end, today)} {_clock(end)}"
    return {
        "start": start,
        "end": end,
        "text": text[0].upper() + text[1:],
        "dispatch_text": f"{_day_word(dispatch_local, today)}, {_clock(dispatch_local)}",
        "batch_id": batch.id,
        "payment_verified": order.payment_status == "Verified",
        "shop_hours": f"{_clock(today.replace(hour=open_hour, minute=0))}–{_clock(today.replace(hour=close_hour, minute=0))}",
    }
