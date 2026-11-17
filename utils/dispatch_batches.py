from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import re
from zoneinfo import ZoneInfo
from flask import current_app
from models import DispatchBatch, ShopSettings, db
SHOP_TZ = ZoneInfo("Africa/Lagos")
NO_ESTIMATE_STATUSES = {"Out for delivery", "Delivered", "Picked up", "Cancelled", "Ready for pickup"}

def order_weight(order):
    total=Decimal("0.000")
    for item in order.items:
        total += Decimal(str(item.requested_weight_kg or item.quantity or 0))
    return max(total, Decimal("0.001"))

def _clock_to_minutes(hour, minute, meridiem):
    hour=int(hour); minute=int(minute or 0); meridiem=(meridiem or "").lower()
    if meridiem == "pm" and hour != 12: hour += 12
    if meridiem == "am" and hour == 12: hour = 0
    return hour*60+minute

def parse_delivery_window(label):
    """Parse common configured labels such as '12pm - 2pm' or '9:00 AM – 11:00 AM'."""
    if not label: return None
    text=str(label).strip().replace("–", "-").replace("—", "-")
    parts=re.split(r"\s+(?:-|to)\s+|\s*-\s*", text, maxsplit=1, flags=re.I)
    if len(parts)!=2: return None
    pattern=r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$"
    left=re.match(pattern, parts[0].strip(), re.I); right=re.match(pattern, parts[1].strip(), re.I)
    if not left or not right: return None
    right_meridiem=right.group(3); left_meridiem=left.group(3) or right_meridiem
    if not left_meridiem or not right_meridiem: return None
    start=_clock_to_minutes(left.group(1),left.group(2),left_meridiem)
    end=_clock_to_minutes(right.group(1),right.group(2),right_meridiem)
    if end <= start: end += 12*60 if end < start+12*60 else 24*60
    return start, end

def _selected_window_bounds(label, now=None):
    parsed=parse_delivery_window(label)
    if not parsed: return None
    now=now or datetime.now(SHOP_TZ)
    start_min,end_min=parsed
    start=now.replace(hour=start_min//60, minute=start_min%60, second=0, microsecond=0)
    end_day=now.date()
    if end_min >= 24*60:
        end_min-=24*60; end_day=now.date()+timedelta(days=1)
    end=now.replace(year=end_day.year, month=end_day.month, day=end_day.day, hour=end_min//60, minute=end_min%60, second=0, microsecond=0)
    if end <= now:
        start += timedelta(days=1); end += timedelta(days=1)
    return start,end

def _next_window_bounds(label, now=None):
    """Return the next not-yet-started occurrence of a configured delivery window."""
    now = now or datetime.now(SHOP_TZ)
    bounds = _selected_window_bounds(label, now)
    if not bounds:
        return None
    start, end = bounds
    if start <= now:
        start += timedelta(days=1)
        end += timedelta(days=1)
    return start, end


def _bounds_for_delivery_date(label, delivery_date):
    """Resolve a configured delivery window on the customer's requested local date."""
    parsed = parse_delivery_window(label)
    if not parsed or not delivery_date:
        return None
    start_min, end_min = parsed
    start_local = datetime.combine(
        delivery_date,
        time(hour=(start_min // 60) % 24, minute=start_min % 60),
        tzinfo=SHOP_TZ,
    )
    end_day = delivery_date + timedelta(days=1) if end_min >= 24 * 60 else delivery_date
    end_min %= 24 * 60
    end_local = datetime.combine(
        end_day,
        time(hour=(end_min // 60) % 24, minute=end_min % 60),
        tzinfo=SHOP_TZ,
    )
    if end_local <= start_local:
        end_local += timedelta(days=1)
    return start_local, end_local


def _batch_for_bounds(order, start_local, end_local):
    settings=ShopSettings.query.get(1)
    limit=max(Decimal("0.001"), Decimal(str(settings.dispatch_batch_weight_limit if settings else 50)))
    start=start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end=end_local.astimezone(timezone.utc).replace(tzinfo=None)
    weight=order_weight(order)
    batch=DispatchBatch.query.filter_by(window_start=start, window_end=end, status="open").order_by(DispatchBatch.id.desc()).first()
    if not batch or Decimal(str(batch.assigned_weight or 0))+weight>limit:
        batch=DispatchBatch(window_start=start,window_end=end,weight_limit=limit,assigned_weight=Decimal("0.000"),status="open")
        db.session.add(batch); db.session.flush()
    batch.assigned_weight=Decimal(str(batch.assigned_weight or 0))+weight
    order.dispatch_batch=batch
    return batch

def assign_dispatch_batch(order, *, next_window=False):
    if order.fulfillment_type != "delivery":
        return None
    # Reassignment must never silently attach an order to an already closed batch.
    order.dispatch_batch = None
    settings = ShopSettings.query.get(1)
    requested_date = getattr(order, "requested_delivery_date", None)

    # A customer-selected date is authoritative: both the dispatch batch and its
    # displayed ETA are built from that calendar date, not from the order timestamp.
    if requested_date and not next_window:
        from utils.delivery_operations import delivery_windows
        configured_windows = delivery_windows(settings)
        preferred = getattr(order, "preferred_delivery_window", None)
        if preferred:
            bounds = _bounds_for_delivery_date(preferred, requested_date)
            if bounds:
                return _batch_for_bounds(order, *bounds)
        dated_candidates = []
        now_local = datetime.now(SHOP_TZ)
        for label in configured_windows:
            bounds = _bounds_for_delivery_date(label, requested_date)
            if bounds and (requested_date != now_local.date() or bounds[0] > now_local):
                dated_candidates.append((bounds[0], label, bounds))
        if dated_candidates:
            _, label, bounds = min(dated_candidates, key=lambda row: row[0])
            order.preferred_delivery_window = label
            return _batch_for_bounds(order, *bounds)
        # If no named delivery windows are configured, keep the dispatch interval
        # on the requested day rather than assigning it to today's rolling batch.
        hours = max(Decimal("0.25"), Decimal(str(settings.dispatch_batch_hours if settings else 2)))
        start_local = datetime.combine(requested_date, time(9, 0), tzinfo=SHOP_TZ)
        if requested_date == now_local.date() and start_local <= now_local:
            start_local = now_local + timedelta(minutes=15)
        return _batch_for_bounds(order, start_local, start_local + timedelta(seconds=float(hours) * 3600))

    if getattr(order, "preferred_delivery_window", None):
        bounds = (_next_window_bounds(order.preferred_delivery_window) if next_window
                  else _selected_window_bounds(order.preferred_delivery_window))
        if bounds:
            return _batch_for_bounds(order, *bounds)
    # Without a still-valid customer preference, choose the nearest configured
    # delivery window rather than an unrelated rolling interval.
    try:
        from utils.delivery_operations import delivery_windows
        candidates=[]
        for label in delivery_windows(settings):
            bounds = (_next_window_bounds(label) if next_window else _selected_window_bounds(label))
            if bounds:
                candidates.append((bounds[0], label, bounds))
        if candidates:
            _, label, bounds=min(candidates, key=lambda row: row[0])
            order.preferred_delivery_window=label
            return _batch_for_bounds(order, *bounds)
    except (TypeError, ValueError):
        pass
    hours=max(Decimal("0.25"), Decimal(str(settings.dispatch_batch_hours if settings else 2)))
    now=datetime.now(SHOP_TZ) if next_window else datetime.now(SHOP_TZ)
    start_local=now.replace(minute=(now.minute // max(1, int(float(hours) * 60))) * max(1, int(float(hours) * 60)), second=0, microsecond=0)
    return _batch_for_bounds(order, start_local, start_local + timedelta(seconds=float(hours) * 3600))

def _clock(moment): return moment.strftime("%I:%M %p").lstrip("0")
def _day_word(moment,today):
    gap=(moment.date()-today.date()).days
    return "today" if gap==0 else ("tomorrow" if gap==1 else moment.strftime("%A %d %b"))
def delivery_estimate(order, now=None):
    batch=getattr(order,"dispatch_batch",None)
    if order is None or order.fulfillment_type!="delivery" or batch is None: return None
    if order.status in NO_ESTIMATE_STATUSES: return None
    now_utc=(now or datetime.utcnow()).replace(tzinfo=timezone.utc)
    start=batch.window_start.replace(tzinfo=timezone.utc).astimezone(SHOP_TZ)
    end=batch.window_end.replace(tzinfo=timezone.utc).astimezone(SHOP_TZ)
    today=now_utc.astimezone(SHOP_TZ)
    text=f"{_day_word(start,today)}, {_clock(start)} – {_clock(end)}"
    return {"start":start,"end":end,"text":text[0].upper()+text[1:],"dispatch_text":f"{_day_word(start,today)}, {_clock(start)}","batch_id":batch.id,"payment_verified":order.payment_status=="Verified","closed":batch.status!="open","preferred_window":getattr(order,"preferred_delivery_window",None)}

def preview_delivery_window(label, now=None, delivery_date=None):
    if delivery_date:
        if isinstance(delivery_date, str):
            try:
                delivery_date = date.fromisoformat(delivery_date)
            except ValueError:
                return ""
        bounds = _bounds_for_delivery_date(label, delivery_date)
    else:
        bounds = _selected_window_bounds(label, now)
    if not bounds:
        return ""
    start, end = bounds
    today = now or datetime.now(SHOP_TZ)
    return f"{_day_word(start, today)}, {_clock(start)} – {_clock(end)}"
