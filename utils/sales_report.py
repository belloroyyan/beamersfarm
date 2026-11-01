"""Sales report figures for the owner (and permitted salespeople)."""
from collections import OrderedDict
from decimal import Decimal
from zoneinfo import ZoneInfo
from datetime import timezone

SHOP_TZ = ZoneInfo("Africa/Lagos")
SUCCESS_STATUSES = {"Delivered", "Picked up"}
D0 = Decimal("0.00")


def _d(value):
    return Decimal(str(value or 0))


def _day(order):
    return order.created_at.replace(tzinfo=timezone.utc).astimezone(SHOP_TZ).date()


def filter_orders_by_text(orders, text):
    text = (text or "").strip()[:120]
    if not text:
        return orders
    low, num = text.casefold(), (int(text) if text.isdigit() else None)
    return [o for o in orders if (num is not None and o.id == num) or low in (o.public_id or "").casefold()
            or low in (o.customer_name or "").casefold() or low in (o.phone or "").casefold() or low in (o.status or "").casefold()]


def build_sales_summary(orders):
    """Definitions:
    gross revenue  = value of every order that was not cancelled (items + delivery fees, after discounts)
    net revenue    = successful deliveries/pickups only, excluding delivery fees
    delivery fees  = fees on non-cancelled orders whose payment was verified
    cancelled      = total value of cancelled orders
    """
    gross = net = fees = cancelled = D0
    by_status, by_channel, days, products = OrderedDict(), {}, OrderedDict(), {}
    successful = 0
    for o in sorted(orders, key=lambda x: x.created_at):
        total, fee = _d(o.total), _d(o.delivery_fee)
        is_cancelled = o.status == "Cancelled"
        row = by_status.setdefault(o.status, {"status": o.status, "count": 0, "value": D0})
        row["count"] += 1; row["value"] += total
        day = days.setdefault(_day(o), {"date": _day(o), "orders": 0, "gross": D0, "net": D0, "fees": D0, "cancelled": D0})
        day["orders"] += 1
        if is_cancelled:
            cancelled += total; day["cancelled"] += total
            continue
        gross += total; day["gross"] += total
        ch = by_channel.setdefault(o.order_channel or "website", {"channel": o.order_channel or "website", "count": 0, "value": D0})
        ch["count"] += 1; ch["value"] += total
        if o.payment_status == "Verified":
            fees += fee; day["fees"] += fee
        if o.status in SUCCESS_STATUSES:
            successful += 1
            net += total - fee; day["net"] += total - fee
            for item in o.items:
                prod = products.setdefault(item.product_name, {"name": item.product_name, "units": Decimal("0"), "sales": D0})
                prod["units"] += _d(item.quantity); prod["sales"] += _d(item.subtotal)
    placed = len(orders)
    live = placed - by_status.get("Cancelled", {"count": 0})["count"]
    return {
        "gross": gross, "net": net, "fees": fees, "cancelled": cancelled,
        "orders_placed": placed, "orders_live": live, "orders_successful": successful,
        "orders_cancelled": by_status.get("Cancelled", {"count": 0})["count"],
        "average_order": (gross / live) if live else D0,
        "by_status": list(by_status.values()), "by_channel": list(by_channel.values()),
        "timeline": list(days.values()),
        "products": sorted(products.values(), key=lambda r: r["sales"], reverse=True),
    }
