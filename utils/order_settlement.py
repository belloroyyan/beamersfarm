from datetime import datetime
from decimal import Decimal

from models import db


def save_order_weights(order, form, *, recorded_by, allowed_statuses=None):
    """Validate and save combined kg weights for an order; return (ok, message)."""
    if order.status == "Cancelled" or order.payment_status != "Verified":
        return False, "Record final weights only for active orders with verified payment."
    if allowed_statuses is not None and order.status not in allowed_statuses:
        return False, "Record outlet weigh-ins after confirmation and before the order is sent to dispatch."

    weighted_items = [item for item in order.items if item.pricing_type == "weight_deposit"]
    if not weighted_items:
        return False, "This order has no weight-priced items to weigh."
    if any(
        record.event_type in {"balance_payment", "refund"} and record.status == "settled"
        for record in order.financial_records
    ):
        return False, "Weights are locked after a balance payment or refund has been recorded. Use the Owner financial history for further adjustments."

    changed = False
    try:
        for item in weighted_items:
            raw = form.get(f"weight_{item.id}", "").strip()
            if not raw:
                if item.actual_weight_kg is not None:
                    changed = True
                item.actual_weight_kg = None
                continue
            weight = Decimal(raw)
            if not weight.is_finite() or weight <= 0 or weight > Decimal("500.000"):
                raise ValueError("Each combined measured weight must be greater than 0 and no more than 500 kg.")
            rounded_weight = weight.quantize(Decimal("0.001"))
            if rounded_weight != weight:
                raise ValueError("Enter weights to no more than three decimal places (for example, 4.250 kg).")
            if item.actual_weight_kg != rounded_weight:
                changed = True
            item.actual_weight_kg = rounded_weight
    except (ArithmeticError, TypeError, ValueError) as error:
        db.session.rollback()
        message = str(error) if isinstance(error, ValueError) and str(error) else "Enter valid weights in kilograms, up to three decimal places."
        return False, message

    if order.weights_complete:
        # If the completed readings change before any settlement is posted, restart the refund clock.
        if changed or order.weighing_completed_at is None:
            order.weighing_completed_at = datetime.utcnow()
        order.weighing_recorded_by = (recorded_by or "Staff")[:120]
        message = "All weight entries are saved. The final customer receipt now shows the calculated total and any balance or refund deadline."
    else:
        order.weighing_completed_at = None
        order.weighing_recorded_by = (recorded_by or "Staff")[:120]
        message = "Weight entries saved. Add the remaining measurements to calculate the final amount."

    db.session.commit()
    return True, message
