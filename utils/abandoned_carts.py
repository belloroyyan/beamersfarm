"""Process abandoned carts without treating failed push delivery as success."""

import json
import logging
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import AbandonedCart, Order, db
from utils.web_push import send_customer_abandoned_cart_push

logger = logging.getLogger(__name__)


def process_abandoned_carts(now=None, limit=100):
    """Process one bounded batch.

    A cart is marked as recovered only when a later order exists, and as
    recovery-sent only after at least one browser subscription accepts the
    push. Missing configuration, missing subscriptions, and delivery failures
    remain eligible for a later scheduled run.
    """
    now = now or datetime.utcnow()
    delay = int(current_app.config.get("ABANDONED_CART_DELAY_HOURS", 24))
    cutoff = now - timedelta(hours=max(1, delay))
    candidates = AbandonedCart.query.filter(
        AbandonedCart.recovery_sent_at.is_(None),
        AbandonedCart.last_activity_at <= cutoff,
        AbandonedCart.recovered_at.is_(None),
    ).order_by(AbandonedCart.last_activity_at.asc()).limit(max(1, int(limit))).all()

    result = {
        "checked": len(candidates),
        "sent": 0,
        "recovered": 0,
        "skipped": 0,
        "failed": 0,
        "pending_retry": 0,
    }

    for abandoned in candidates:
        try:
            customer = abandoned.customer
            if not customer or not customer.active:
                db.session.delete(abandoned)
                result["skipped"] += 1
                db.session.commit()
                continue

            recent_order = Order.query.filter(
                Order.customer_id == customer.id,
                Order.created_at > abandoned.last_activity_at,
            ).first()
            if recent_order:
                abandoned.recovered_at = now
                db.session.delete(abandoned)
                result["recovered"] += 1
                db.session.commit()
                continue

            try:
                payload = json.loads(abandoned.cart_json or "{}")
            except (TypeError, ValueError):
                payload = None
            if not isinstance(payload, dict) or not payload:
                db.session.delete(abandoned)
                result["skipped"] += 1
                db.session.commit()
                continue

            delivery = send_customer_abandoned_cart_push(customer, abandoned.subtotal)
            sent = int(delivery.get("sent") or 0)
            failed = int(delivery.get("failed") or 0)
            total = int(delivery.get("total") or 0)

            if sent > 0:
                # This is a per-customer recovery marker. Once at least one
                # registered device receives the push, do not resend to that
                # customer on every cron run (which could duplicate alerts).
                abandoned.recovery_sent_at = now
                result["sent"] += sent
            elif failed > 0:
                result["failed"] += failed
                result["pending_retry"] += 1
                logger.warning(
                    "Abandoned-cart push remains pending for customer %s; %s delivery attempt(s) failed.",
                    customer.id,
                    failed,
                )
            else:
                # Not configured or no active subscription: keep the cart
                # eligible so a later run can retry after setup/subscription.
                result["skipped"] += 1
                result["pending_retry"] += 1
                if not delivery.get("configured"):
                    logger.info(
                        "Abandoned-cart push is not configured or enabled for customer %s; leaving it pending.",
                        customer.id,
                    )
                elif total == 0:
                    logger.info(
                        "Customer %s has no active push subscriptions; leaving abandoned cart pending.",
                        customer.id,
                    )

            # Commit each cart independently so one bad record does not roll
            # back successful processing of earlier carts in this batch.
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            result["failed"] += 1
            result["pending_retry"] += 1
            logger.exception("Database error while processing abandoned cart %s.", abandoned.id)
        except Exception:
            db.session.rollback()
            result["failed"] += 1
            result["pending_retry"] += 1
            logger.exception("Unexpected error while processing abandoned cart %s.", abandoned.id)

    # Persist any final deletions/changes made in branches that continued.
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not commit final abandoned-cart batch changes.")
        result["failed"] += 1
    return result
