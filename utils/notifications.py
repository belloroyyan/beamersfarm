"""Notification helpers used by the Phase 1 delivery foundation."""

import re


def normalize_nigerian_phone(value):
    """Return a compact Nigerian MSISDN without a leading plus sign.

    This intentionally does not claim that a number is deliverable; the real
    provider integration will perform final validation before sending.
    """
    digits = re.sub(r"\D+", "", value or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "234" + digits[1:]
    elif digits.startswith("234"):
        digits = digits
    return digits


def build_order_confirmed_message(order):
    """Build the exact text that a future WhatsApp provider will send."""
    amount = f"₦{order.total:,.2f}"
    return (
        f"Hello {order.customer_name}, your Beamers Farm order "
        f"#{order.public_id} has been confirmed. Total: {amount}. "
        "We are preparing your order for delivery within Osogbo. "
        "For questions, contact Beamers Farm on WhatsApp: 08062074302."
    )
