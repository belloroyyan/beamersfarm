import json
from datetime import datetime, timedelta

from flask import current_app

from models import AbandonedCart, Order, db
from utils.web_push import send_customer_abandoned_cart_push


def process_abandoned_carts(now=None, limit=100):
    now = now or datetime.utcnow()
    delay = int(current_app.config.get("ABANDONED_CART_DELAY_HOURS", 24))
    cutoff = now - timedelta(hours=max(1, delay))
    candidates = AbandonedCart.query.filter(
        AbandonedCart.recovery_sent_at.is_(None),
        AbandonedCart.last_activity_at <= cutoff,
        AbandonedCart.recovered_at.is_(None),
    ).order_by(AbandonedCart.last_activity_at.asc()).limit(limit).all()
    result = {"checked": len(candidates), "sent": 0, "recovered": 0, "skipped": 0, "failed": 0}
    for abandoned in candidates:
        customer = abandoned.customer
        if not customer or not customer.active:
            db.session.delete(abandoned)
            result["skipped"] += 1
            continue
        recent_order = Order.query.filter(
            Order.customer_id == customer.id,
            Order.created_at > abandoned.last_activity_at,
        ).first()
        if recent_order:
            abandoned.recovered_at = now
            db.session.delete(abandoned)
            result["recovered"] += 1
            continue
        try:
            payload = json.loads(abandoned.cart_json or "{}")
            if not isinstance(payload, dict) or not payload:
                db.session.delete(abandoned)
                result["skipped"] += 1
                continue
        except (TypeError, ValueError):
            db.session.delete(abandoned)
            result["skipped"] += 1
            continue
        delivery = send_customer_abandoned_cart_push(customer, abandoned.subtotal)
        abandoned.recovery_sent_at = now
        if delivery.get("sent"):
            result["sent"] += delivery["sent"]
        elif delivery.get("failed"):
            result["failed"] += delivery["failed"]
        else:
            result["skipped"] += 1
    db.session.commit()
    return result
