from datetime import datetime, timedelta
from decimal import Decimal

from models import AbandonedCart, Customer, Order, Product, WholesaleOrder, db


def customer_segment(customer, now=None):
    now = now or datetime.utcnow()
    orders = sorted(customer.orders or [], key=lambda order: order.created_at or datetime.min, reverse=True)
    total = sum((Decimal(str(order.total or 0)) for order in orders if order.status not in {"Cancelled", "Declined"}), Decimal("0.00"))
    last_order = orders[0].created_at if orders else None
    days_since = (now - last_order).days if last_order else None
    if not orders:
        segment = "New"
    elif days_since is not None and days_since >= 60:
        segment = "At risk"
    elif len(orders) >= 2 and total >= Decimal("100000"):
        segment = "High value"
    elif len(orders) >= 2:
        segment = "Repeat"
    else:
        segment = "New"
    return {"name": segment, "orders": len(orders), "total": total, "last_order": last_order, "days_since": days_since}


def customer_segments(customers):
    return {customer.id: customer_segment(customer) for customer in customers}


def abandoned_cart_report(limit=10):
    carts = AbandonedCart.query.filter(AbandonedCart.recovery_sent_at.is_(None)).order_by(AbandonedCart.last_activity_at.asc()).limit(limit).all()
    return {"count": AbandonedCart.query.filter(AbandonedCart.recovery_sent_at.is_(None)).count(), "oldest": carts[0] if carts else None, "items": carts}


def operational_snapshot():
    today = datetime.utcnow().date()
    return {
        "customers": Customer.query.filter_by(active=True).count(),
        "abandoned_carts": AbandonedCart.query.filter(AbandonedCart.recovery_sent_at.is_(None)).count(),
        "wholesale_open": WholesaleOrder.query.filter(WholesaleOrder.status.in_(["New", "Contacted", "Quoted", "Approved"])).count(),
        "low_stock_products": Product.query.filter(Product.active.is_(True), Product.stock <= Product.low_stock_threshold).count(),
        "sales_today": sum((Decimal(str(order.total or 0)) for order in Order.query.filter(db.func.date(Order.created_at) == today, Order.status.notin_(["Cancelled", "Declined"])).all()), Decimal("0.00")),
    }
