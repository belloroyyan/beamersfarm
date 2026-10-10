import json
import logging

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import (
    CustomerPushSubscription,
    SalespersonAccount,
    StaffPushSubscription,
    db,
    order_customer_push_subscriptions,
)
from utils.salesperson_permissions import salesperson_has_permission


logger = logging.getLogger(__name__)


def web_push_is_configured():
    return all(
        current_app.config.get(key)
        for key in ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT")
    )


def _send_to_subscriptions(subscriptions, title, body, url, audience):
    result = {"configured": True, "total": len(subscriptions), "sent": 0, "failed": 0, "expired": 0}
    if not subscriptions:
        return result

    # Keep notification contents generic; never include customer contact or payment data.
    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        from pywebpush import WebPushException, webpush
        from py_vapid import Vapid
    except ImportError:
        logger.error("Web Push is configured, but pywebpush is unavailable.")
        result["failed"] = result["total"]
        return result

    private_key = current_app.config["VAPID_PRIVATE_KEY"]
    if isinstance(private_key, str) and private_key.startswith("-----BEGIN "):
        private_key = Vapid.from_pem(private_key.encode("utf-8"))

    expired_records = []
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": current_app.config["VAPID_SUBJECT"]},
                ttl=600,
                timeout=5,
            )
            result["sent"] += 1
        except WebPushException as error:
            status_code = getattr(error, "status_code", None)
            if status_code in (404, 410):
                expired_records.append(subscription)
                result["expired"] += 1
            else:
                result["failed"] += 1
                logger.warning("%s push delivery failed (HTTP %s).", audience, status_code or "unknown")
        except Exception:
            result["failed"] += 1
            logger.exception("Unexpected %s push delivery failure.", audience)

    if expired_records:
        try:
            if audience == "customer":
                expired_ids = [subscription.id for subscription in expired_records]
                db.session.execute(
                    order_customer_push_subscriptions.delete().where(
                        order_customer_push_subscriptions.c.subscription_id.in_(expired_ids)
                    )
                )
            for subscription in expired_records:
                db.session.delete(subscription)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Could not remove expired %s push subscriptions.", audience)

    return result


def send_staff_push(staff_role, title, body, url):
    """Send a minimal role-targeted push to every opted-in device for that role."""
    if staff_role not in {"owner", "dispatch_rider", "salesperson"}:
        return {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}
    if not web_push_is_configured():
        return {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}

    try:
        subscriptions_query = StaffPushSubscription.query.filter_by(staff_role=staff_role)
        if staff_role == "salesperson":
            eligible_ids = [
                account.id for account in SalespersonAccount.query.filter_by(active=True).all()
                if salesperson_has_permission(account, "receive_order_alerts")
            ]
            if not eligible_ids:
                return {"configured": True, "total": 0, "sent": 0, "failed": 0, "expired": 0}
            subscriptions_query = subscriptions_query.filter(
                StaffPushSubscription.salesperson_account_id.in_(eligible_ids)
            )
        else:
            subscriptions_query = subscriptions_query.filter(
                StaffPushSubscription.salesperson_account_id.is_(None)
            )
        subscriptions = subscriptions_query.order_by(StaffPushSubscription.id.asc()).all()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read %s push subscriptions.", staff_role)
        return {"configured": True, "total": 0, "sent": 0, "failed": 1, "expired": 0}
    return _send_to_subscriptions(subscriptions, title, body, url, staff_role)


def send_customer_order_confirmed_push(order, subscription_ids=None):
    """Notify devices explicitly associated with this order when it is confirmed."""
    if not web_push_is_configured():
        return {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}

    try:
        subscriptions = list(order.customer_push_subscriptions)
        if subscription_ids is not None:
            allowed = set(subscription_ids)
            subscriptions = [item for item in subscriptions if item.id in allowed]
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read customer push subscriptions for order %s.", order.id)
        return {"configured": True, "total": 0, "sent": 0, "failed": 1, "expired": 0}

    return _send_to_subscriptions(
        subscriptions,
        "Order confirmed",
        "Your order is confirmed and is being prepared.",
        "/",
        "customer order confirmation",
    )


def send_customer_order_out_for_delivery_push(order, subscription_ids=None):
    """Notify devices associated with a delivery order when it leaves for delivery."""
    if order.fulfillment_type != "delivery":
        return {"configured": web_push_is_configured(), "total": 0, "sent": 0, "failed": 0, "expired": 0}
    if not web_push_is_configured():
        return {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}

    try:
        subscriptions = list(order.customer_push_subscriptions)
        if subscription_ids is not None:
            allowed = set(subscription_ids)
            subscriptions = [item for item in subscriptions if item.id in allowed]
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read customer push subscriptions for delivery order %s.", order.id)
        return {"configured": True, "total": 0, "sent": 0, "failed": 1, "expired": 0}

    return _send_to_subscriptions(
        subscriptions,
        "Order out for delivery",
        "Your order is on its way. Please keep your phone nearby to receive it.",
        "/track-order",
        "customer delivery status",
    )


def send_dispatch_assignment_push():
    return send_staff_push(
        "dispatch_rider",
        "New delivery assigned",
        "A new order is in the dispatch queue. Sign in to review the delivery.",
        "/dispatch/",
    )


def send_owner_new_order_push():
    return send_staff_push(
        "owner",
        "New order received",
        "A customer placed a new order. Sign in to the owner desk to review it.",
        "/admin/",
    )


def send_owner_low_stock_push(product):
    return send_staff_push(
        "owner",
        "Low stock alert",
        f"{product.name} is low on stock ({product.stock:g} remaining). Review inventory in the owner desk.",
        "/admin/inventory",
    )


def send_owner_wholesale_request_push():
    return send_staff_push(
        "owner",
        "New wholesale request",
        "A business sent a new wholesale request. Review quantities and follow up from the owner desk.",
        "/admin/wholesale-orders",
    )


def send_salesperson_new_order_push():
    return send_staff_push(
        "salesperson",
        "New order received",
        "A customer placed a new order. Sign in to the sales desk to review it.",
        "/sales/",
    )
