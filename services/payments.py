"""Paystack payment helpers with server-side verification and idempotent updates."""

import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from flask import current_app

from models import Order, OrderFinancialRecord, db

PAYSTACK_API = "https://api.paystack.co"


def paystack_is_configured():
    return bool(
        current_app.config.get("PAYSTACK_ENABLED")
        and current_app.config.get("PAYSTACK_SECRET_KEY")
        and current_app.config.get("PAYSTACK_PUBLIC_KEY")
    )


def _api_request(method, path, payload=None):
    secret = current_app.config.get("PAYSTACK_SECRET_KEY", "")
    body = None
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"{PAYSTACK_API}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError("Paystack could not be reached. Please try again or use bank transfer.") from exc


def initialize_paystack_transaction(order, callback_url):
    if not paystack_is_configured():
        raise RuntimeError("Online payment is not enabled yet. Please choose bank transfer.")
    reference = f"BF-{order.public_id}-{secrets.token_hex(5)}"
    amount_kobo = int(
        (Decimal(str(order.total)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    response = _api_request(
        "POST",
        "/transaction/initialize",
        {
            "email": order.email,
            "amount": str(amount_kobo),
            "currency": "NGN",
            "reference": reference,
            "callback_url": callback_url,
            "channels": ["card", "bank", "bank_transfer", "ussd", "qr", "mobile_money"],
            "metadata": json.dumps({"order_public_id": order.public_id}),
        },
    )
    if not response.get("status") or not response.get("data", {}).get("authorization_url"):
        raise RuntimeError(response.get("message") or "Paystack did not create a checkout session.")
    data = response["data"]
    order.payment_method = "paystack"
    order.payment_provider = "paystack"
    order.payment_reference = data.get("reference") or reference
    order.payment_status = "Pending"
    order.payment_initiated_at = datetime.utcnow()
    db.session.commit()
    return data["authorization_url"]


def verify_paystack_transaction(reference):
    if not paystack_is_configured():
        raise RuntimeError("Online payment is not enabled.")
    return _api_request("GET", f"/transaction/verify/{urllib.parse.quote(reference, safe='')}")


def valid_webhook_signature(raw_body, signature):
    secret = current_app.config.get("PAYSTACK_SECRET_KEY", "")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def mark_successful_paystack_payment(order, transaction):
    """Mark a matching successful transaction paid; return (ok, message)."""
    if not order or order.payment_method != "paystack":
        return False, "This transaction is not a Paystack order."
    reference = str(transaction.get("reference") or "")
    expected_reference = order.payment_reference or ""
    try:
        amount = int(transaction.get("amount"))
    except (TypeError, ValueError):
        amount = None
    currency = str(transaction.get("currency") or "").upper()
    expected_amount = int(
        (Decimal(str(order.total)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if reference != expected_reference:
        return False, "The Paystack reference does not match this order."
    if str(transaction.get("status", "")).lower() != "success":
        order.payment_status = "Failed"
        db.session.commit()
        return False, "Paystack has not reported a successful payment."
    if amount != expected_amount or currency != "NGN":
        return False, "The Paystack amount or currency does not match this order."
    if order.payment_status == "Verified":
        return True, "Payment was already verified."

    now = datetime.utcnow()
    order.payment_status = "Verified"
    order.payment_verified_at = now
    order.payment_verified_by_role = "paystack"
    order.payment_verified_by_name = "Paystack"
    order.payment_channel = str(transaction.get("channel") or "online")[:30]
    initial_record = next(
        (record for record in order.financial_records if record.event_type == "initial_payment"), None
    )
    if initial_record is None:
        initial_record = OrderFinancialRecord(
            order=order,
            event_type="initial_payment",
            amount=order.total,
            payment_method="paystack",
            status="settled",
            reference=reference,
            notes="Payment verified automatically by Paystack.",
        )
        db.session.add(initial_record)
    else:
        initial_record.status = "settled"
        initial_record.payment_method = "paystack"
        initial_record.reference = reference[:160]
        initial_record.notes = "Payment verified automatically by Paystack."
        initial_record.settled_at = now
    db.session.commit()
    return True, "Payment verified automatically by Paystack. The order is ready for owner confirmation."
