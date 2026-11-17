import hashlib
import hmac
import json
import logging

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import (
    CustomerPushSubscription,
    Customer,
    SalespersonAccount,
    StaffPushSubscription,
    db,
    order_customer_push_subscriptions,
)
from utils.notifications import normalize_nigerian_phone
from utils.salesperson_permissions import salesperson_has_permission

logger = logging.getLogger(__name__)


def web_push_is_configured():
    return all(current_app.config.get(key) for key in ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT"))


def _send_to_subscriptions(subscriptions, title, body, url, audience):
    result = {"configured": True, "total": len(subscriptions), "sent": 0, "failed": 0, "expired": 0}
    if not subscriptions:
        return result
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
                subscription_info={"endpoint": subscription.endpoint, "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
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
                db.session.execute(order_customer_push_subscriptions.delete().where(order_customer_push_subscriptions.c.subscription_id.in_(expired_ids)))
            for subscription in expired_records:
                db.session.delete(subscription)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("Could not remove expired %s push subscriptions.", audience)
    return result


def send_staff_push(staff_role, title, body, url):
    if staff_role not in {"owner", "dispatch_rider", "salesperson"} or not web_push_is_configured():
        return {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}
    try:
        subscriptions_query = StaffPushSubscription.query.filter_by(staff_role=staff_role)
        if staff_role == "salesperson":
            eligible_ids = [account.id for account in SalespersonAccount.query.filter_by(active=True).all() if salesperson_has_permission(account, "receive_order_alerts")]
            if not eligible_ids:
                return {"configured": True, "total": 0, "sent": 0, "failed": 0, "expired": 0}
            subscriptions_query = subscriptions_query.filter(StaffPushSubscription.salesperson_account_id.in_(eligible_ids))
        else:
            subscriptions_query = subscriptions_query.filter(StaffPushSubscription.salesperson_account_id.is_(None))
        subscriptions = subscriptions_query.order_by(StaffPushSubscription.id.asc()).all()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read %s push subscriptions.", staff_role)
        return {"configured": True, "total": 0, "sent": 0, "failed": 1, "expired": 0}
    return _send_to_subscriptions(subscriptions, title, body, url, staff_role)


def send_customer_order_confirmed_push(order, subscription_ids=None):
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
    return _send_to_subscriptions(subscriptions, "Order confirmed", "Your order is confirmed and is being prepared.", "/", "customer order confirmation")


def send_customer_order_out_for_delivery_push(order, subscription_ids=None):
    if order.fulfillment_type != "delivery" or not web_push_is_configured():
        return {"configured": web_push_is_configured(), "total": 0, "sent": 0, "failed": 0, "expired": 0}
    try:
        subscriptions = list(order.customer_push_subscriptions)
        if subscription_ids is not None:
            allowed = set(subscription_ids)
            subscriptions = [item for item in subscriptions if item.id in allowed]
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read customer push subscriptions for delivery order %s.", order.id)
        return {"configured": True, "total": 0, "sent": 0, "failed": 1, "expired": 0}
    return _send_to_subscriptions(subscriptions, "Order out for delivery", "Your order is on its way. Please keep your phone nearby to receive it.", "/track-order", "customer delivery status")


def _customer_push_key(phone):
    normalized = normalize_nigerian_phone(phone) or " ".join((phone or "").split()).casefold()
    return hmac.new(str(current_app.config["SECRET_KEY"]).encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def send_customer_event_push(title, body, url="/account", *, customer=None, order=None, broadcast=False):
    """Send opted-in customer push alerts for account-wide events or a specific customer/order."""
    empty = {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}
    if not web_push_is_configured():
        return empty
    try:
        keys = set()
        subscriptions = []
        if broadcast:
            customers = Customer.query.filter_by(active=True, push_notifications_enabled=True).filter(Customer.deleted_at.is_(None)).all()
            keys = {_customer_push_key(person.phone) for person in customers if person.phone}
        elif customer is not None:
            if customer.active and customer.push_notifications_enabled:
                keys.add(_customer_push_key(customer.phone))
        elif order is not None:
            linked_customer = order.customer
            if linked_customer is None:
                # Guest orders can have a directly linked, explicitly opted-in device.
                subscriptions.extend(list(order.customer_push_subscriptions))
            elif linked_customer.active and linked_customer.push_notifications_enabled:
                keys.add(_customer_push_key(linked_customer.phone))
                subscriptions.extend(list(order.customer_push_subscriptions))
        if keys:
            subscriptions.extend(
                CustomerPushSubscription.query.filter(CustomerPushSubscription.customer_key.in_(keys))
                .order_by(CustomerPushSubscription.id.asc()).all()
            )
        # Deduplicate subscriptions that are linked to both the order and customer key.
        unique = {item.id: item for item in subscriptions}
        return _send_to_subscriptions(list(unique.values()), title, body, url, "customer")
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not resolve customer push subscriptions for event %s.", title)
        return {**empty, "configured": True, "failed": 1}


def send_customer_abandoned_cart_push(customer, cart_total=None):
    empty = {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}
    if not customer or not customer.active or not customer.push_notifications_enabled or not web_push_is_configured():
        return empty
    try:
        subscriptions = CustomerPushSubscription.query.filter_by(customer_key=_customer_push_key(customer.phone)).order_by(CustomerPushSubscription.id.asc()).all()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Could not read abandoned-cart subscriptions for customer %s.", customer.id)
        return {**empty, "configured": True, "failed": 1}
    return _send_to_subscriptions(subscriptions, "Your Beamers Farms cart is waiting", "You left items in your cart. Come back when you are ready to complete your order.", "/cart", "customer")


def send_dispatch_assignment_push():
    return send_staff_push("dispatch_rider", "New delivery assigned", "A new order is in the dispatch queue. Sign in to review the delivery.", "/dispatch/")


def send_owner_new_order_push():
    return send_staff_push("owner", "New order received", "A customer placed a new order. Sign in to the owner desk to review it.", "/admin/")


def send_owner_low_stock_push(product):
    return send_staff_push("owner", "Low stock alert", f"{product.name} is low on stock ({product.stock:g} remaining). Review inventory in the owner desk.", "/admin/inventory")


def send_owner_wholesale_request_push():
    return send_staff_push("owner", "New wholesale request", "A business sent a new wholesale request. Review quantities and follow up from the owner desk.", "/admin/wholesale-orders")


def send_salesperson_new_order_push():
    return send_staff_push("salesperson", "New order received", "A customer placed a new order. Sign in to the sales desk to review it.", "/sales/")


def send_owner_complaint_push(complaint):
    return send_staff_push("owner", "New customer complaint", f"A customer reported: {complaint.subject}. Open Customer care to review it.", "/admin/complaints")

def send_customer_community_reply_push(customer, post):
    empty = {"configured": False, "total": 0, "sent": 0, "failed": 0, "expired": 0}
    if not customer or not customer.active or not customer.push_notifications_enabled or not web_push_is_configured():
        return empty
    try:
        subscriptions = CustomerPushSubscription.query.filter_by(customer_key=_customer_push_key(customer.phone)).order_by(CustomerPushSubscription.id.asc()).all()
    except SQLAlchemyError:
        db.session.rollback(); logger.exception("Could not read community subscriptions for customer %s", customer.id)
        return {**empty, "configured": True, "failed": 1}
    return _send_to_subscriptions(subscriptions, "Beamers Farms replied", "The Beamers Farms team replied to your community post.", "/community", "customer community")
