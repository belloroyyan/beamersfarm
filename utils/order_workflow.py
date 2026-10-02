from datetime import datetime
from decimal import Decimal

from models import OrderFinancialRecord, OrderNotification, db
from utils.notifications import build_order_confirmed_message, normalize_nigerian_phone
from utils.web_push import (
    send_customer_order_confirmed_push,
    send_dispatch_assignment_push,
)

ORDER_STATUSES = [
    "Received", "Confirmed", "Preparing", "Out for delivery", "Ready for pickup",
    "Delivered", "Picked up", "Cancelled",
]
PAYMENT_REQUIRED_STATUSES = {
    "Confirmed", "Preparing", "Out for delivery", "Ready for pickup", "Delivered", "Picked up",
}
DELIVERY_ONLY_STATUSES = {"Out for delivery", "Delivered"}
PICKUP_ONLY_STATUSES = {"Ready for pickup", "Picked up"}


def update_order_status(
    order, new_status, *, verify_payment=False, actor="owner", actor_name=None,
    verification_reference="",
):
    """Return (ok, message); commit a valid status/payment transition and send alerts."""
    if new_status not in ORDER_STATUSES:
        return False, "Choose a valid order status."
    if verify_payment and actor not in {"owner", "salesperson"}:
        return False, "Only the Owner or an authorized Salesperson can verify payment in the business bank account."
    if actor != "salesperson" and order.fulfillment_type == "pickup" and new_status in DELIVERY_ONLY_STATUSES:
        return False, "Farm-pickup orders cannot be assigned to delivery."
    if actor != "salesperson" and order.fulfillment_type != "pickup" and new_status in PICKUP_ONLY_STATUSES:
        return False, "Delivery orders cannot use pickup-only statuses."

    previous_status = order.status
    status_changed = new_status != previous_status
    payment_verified_now = False
    if verify_payment and new_status not in {"Received", "Confirmed"}:
        return False, "Verify payment while the order is Received, or select Confirmed to verify and confirm together."
    if verify_payment and order.status not in {"Received", "Confirmed"}:
        return False, "Payment can only be verified before fulfillment begins."
    if verify_payment and order.payment_status != "Verified":
        payment_verified_now = True
    if new_status in PAYMENT_REQUIRED_STATUSES and order.payment_status != "Verified":
        if actor not in {"owner", "salesperson"} or new_status != "Confirmed" or not verify_payment:
            return False, (
                "This order cannot be confirmed or progressed until the amount due now appears in the "
                "business bank account. The Owner or an authorized Salesperson must verify payment first."
            )
        payment_verified_now = True

    if status_changed and previous_status == "Cancelled" and new_status != "Cancelled":
        for item in order.items:
            if item.product and item.product.stock < item.quantity:
                return False, f"Not enough stock to reopen {item.product_name}."

    if status_changed and new_status == "Cancelled" and previous_status != "Cancelled":
        for item in order.items:
            if item.product:
                item.product.stock += item.quantity
    elif status_changed and previous_status == "Cancelled" and new_status != "Cancelled":
        for item in order.items:
            if item.product:
                item.product.stock -= item.quantity

    if payment_verified_now:
        order.payment_status = "Verified"
        order.payment_verified_at = datetime.utcnow()
        order.payment_verified_by_role = actor if actor in {"owner", "salesperson"} else "owner"
        order.payment_verified_by_name = actor_name.strip()[:120] if actor == "salesperson" and actor_name else None
        initial_record = next(
            (record for record in order.financial_records if record.event_type == "initial_payment"),
            None,
        )
        if initial_record is None and Decimal(str(order.total or 0)) > 0:
            initial_record = OrderFinancialRecord(
                order=order,
                event_type="initial_payment",
                amount=order.total,
                status="pending",
                payment_method="bank transfer",
                notes="Pay-now amount includes item prices or deposits and the selected fulfillment fee.",
            )
            db.session.add(initial_record)
        if initial_record is not None:
            initial_record.status = "settled"
            initial_record.settled_at = order.payment_verified_at
            initial_record.recorded_by = (actor_name or ("Owner" if actor == "owner" else "Salesperson"))[:120]
            if verification_reference:
                initial_record.reference = verification_reference.strip()[:160]

    if status_changed:
        order.status = new_status
    if status_changed and previous_status != "Confirmed" and new_status == "Confirmed" and order.whatsapp_opt_in:
        existing = OrderNotification.query.filter_by(
            order_id=order.id,
            channel="whatsapp",
            event="order_confirmed",
        ).first()
        if existing is None:
            db.session.add(
                OrderNotification(
                    order=order,
                    channel="whatsapp",
                    event="order_confirmed",
                    recipient=normalize_nigerian_phone(order.phone),
                    message=build_order_confirmed_message(order),
                    status="pending",
                )
            )

    if not status_changed and not payment_verified_now:
        return True, "No order or payment changes were made."

    db.session.commit()
    if status_changed and new_status == "Confirmed" and previous_status != "Confirmed":
        send_customer_order_confirmed_push(order)
    if status_changed and new_status == "Out for delivery" and previous_status != "Out for delivery":
        push_result = send_dispatch_assignment_push()
        if not push_result["configured"]:
            return True, "Order assigned to dispatch. Push alerts are not configured yet; the rider can refresh the queue."
        if push_result["failed"] and not push_result["total"]:
            return True, "Order assigned to dispatch, but push subscriptions could not be read. The rider can refresh the queue."
        if not push_result["total"]:
            return True, "Order assigned to dispatch. No rider device has enabled push alerts yet."
        if push_result["sent"]:
            return True, f"Order assigned to dispatch. Push alert sent to {push_result['sent']} device(s)."
        return True, "Order assigned to dispatch, but the push alert could not be delivered. The rider can refresh the queue."

    if payment_verified_now and new_status == "Confirmed" and order.whatsapp_opt_in:
        return True, "Payment verified in the business bank account and order confirmed. WhatsApp notification queued."
    if payment_verified_now and new_status == "Confirmed":
        return True, "Payment verified in the business bank account and order confirmed."
    if payment_verified_now:
        return True, "Payment verified in the business bank account. The order remains Received until confirmation."
    if status_changed and new_status == "Confirmed" and order.whatsapp_opt_in:
        return True, "Order confirmed. WhatsApp notification queued for the scheduled sender."
    return True, "Order status updated."
