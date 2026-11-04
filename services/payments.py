"""OPay Cashier hosted checkout and server-side payment verification."""

import hashlib
import hmac
import json
import logging
import secrets
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlsplit

from sqlalchemy import update

from flask import current_app

from models import Order, OrderFinancialRecord, db

logger = logging.getLogger(__name__)


def _has_public_https_origin():
    origin = str(current_app.config.get("PUBLIC_ORIGIN") or "").strip()
    if not origin:
        return False
    try:
        parsed = urlsplit(origin)
        parsed.port  # Accessing this validates any explicit port.
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def opay_is_configured():
    return bool(
        current_app.config.get("OPAY_ENABLED")
        and current_app.config.get("OPAY_MERCHANT_ID")
        and current_app.config.get("OPAY_PUBLIC_KEY")
        and current_app.config.get("OPAY_PRIVATE_KEY")
        and _has_public_https_origin()
    )


def _api_base():
    return "https://liveapi.opaycheckout.com" if current_app.config.get("OPAY_ENVIRONMENT") == "live" else "https://testapi.opaycheckout.com"


def _api_request(path, payload, authorization):
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{_api_base()}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {authorization}",
            "MerchantId": current_app.config["OPAY_MERCHANT_ID"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("OPay API returned HTTP %s on %s.", exc.code, path)
        raise RuntimeError("OPay could not process the payment request. Please try again or use manual OPay transfer.") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("OPay API connection or response failed on %s.", path)
        raise RuntimeError("OPay could not be reached. Please try again or use manual OPay transfer.") from exc
    if str(result.get("code", "")) != "00000":
        message = str(result.get("message") or "OPay did not accept the request.")[:180]
        raise RuntimeError(f"OPay: {message}")
    return result


def _expected_amount_kobo(order):
    return int((Decimal(str(order.total)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _safe_cashier_url(value):
    try:
        parsed = urlsplit(str(value or ""))
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and (host == "opaycheckout.com" or host.endswith(".opaycheckout.com"))
            and parsed.username is None
            and parsed.password is None
            and bool(parsed.path)
        )
    except ValueError:
        return False


def initialize_opay_checkout(order, return_url, callback_url, cancel_url):
    """Create/reuse an OPay cashier session; never mark an order paid here."""
    if not opay_is_configured():
        raise RuntimeError("OPay online checkout is not configured yet. Please use manual OPay transfer.")
    if order.payment_status == "Verified":
        raise RuntimeError("This order is already paid.")
    if order.payment_checkout_url and order.payment_status == "Pending" and _safe_cashier_url(order.payment_checkout_url):
        return order.payment_checkout_url

    if order.payment_status == "Failed" or not order.payment_reference:
        order.payment_reference = f"BF-{order.public_id}-{secrets.token_hex(6).upper()}"
        order.payment_checkout_url = None
    reference = order.payment_reference
    order.payment_method = "opay_checkout"
    order.payment_provider = "opay"
    order.payment_status = "Pending"
    order.payment_initiated_at = datetime.utcnow()
    order.payment_failure_reason = None
    db.session.commit()

    user_info = {
        "userName": order.customer_name[:120],
        "userMobile": order.phone[:40],
    }
    if order.email:
        user_info["userEmail"] = order.email[:160]
    payload = {
        "country": "NG",
        "reference": reference,
        "amount": {"total": _expected_amount_kobo(order), "currency": "NGN"},
        "returnUrl": return_url,
        "callbackUrl": callback_url,
        "cancelUrl": cancel_url,
        "displayName": "Beamers Farms",
        "customerVisitSource": "BROWSER",
        "expireAt": 30,
        "userInfo": user_info,
        "product": {
            "name": "Beamers Farms order",
            "description": f"Order {order.public_id} — full amount due",
        },
    }
    try:
        response = _api_request(
            "/api/v1/international/cashier/create",
            payload,
            current_app.config["OPAY_PUBLIC_KEY"],
        )
        data = response.get("data") or {}
        cashier_url = data.get("cashierUrl")
        returned_reference = str(data.get("reference") or reference)
        amount = data.get("amount") or {}
        if returned_reference != reference:
            raise RuntimeError("OPay returned a different payment reference.")
        if not isinstance(cashier_url, str) or not _safe_cashier_url(cashier_url):
            raise RuntimeError("OPay returned an invalid hosted checkout address.")
        if int(amount.get("total", -1)) != _expected_amount_kobo(order) or str(amount.get("currency", "")).upper() != "NGN":
            raise RuntimeError("The OPay checkout amount or currency did not match this order.")
        order.payment_checkout_url = cashier_url[:1000]
        db.session.commit()
        return order.payment_checkout_url
    except Exception as exc:
        order.payment_status = "Failed"
        order.payment_failure_reason = str(exc)[:500]
        order.payment_checkout_url = None
        db.session.commit()
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError("OPay could not create a checkout session. Please use manual OPay transfer.") from exc


def verify_opay_transaction(reference):
    """Query OPay using an HMAC-SHA512 signature over sorted request JSON."""
    if not opay_is_configured():
        raise RuntimeError("OPay verification is not configured.")
    if not reference or len(reference) > 160:
        raise RuntimeError("The OPay payment reference is invalid.")
    payload = {"country": "NG", "reference": reference}
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    signature = hmac.new(
        current_app.config["OPAY_PRIVATE_KEY"].encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()
    response = _api_request("/api/v1/international/cashier/status", payload, signature)
    return response.get("data") or {}


def valid_opay_callback_signature(payload, signature):
    """Validate OPay's documented canonical callback HMAC-SHA3-512 signature."""
    if not opay_is_configured() or not isinstance(payload, dict) or not signature:
        return False
    required = ("amount", "currency", "reference", "status", "timestamp", "transactionId")
    if any(payload.get(name) is None for name in required):
        return False
    refunded = "t" if payload.get("refunded") is True else "f"
    canonical = (
        f'{{Amount:"{payload.get("amount", "")}",Currency:"{payload.get("currency", "")}",'
        f'Reference:"{payload.get("reference", "")}",Refunded:{refunded},Status:"{payload.get("status", "")}",'
        f'Timestamp:"{payload.get("timestamp", "")}",Token:"{payload.get("token") or ""}",'
        f'TransactionID:"{payload.get("transactionId", "")}"}}'
    )
    expected = hmac.new(
        current_app.config["OPAY_PRIVATE_KEY"].encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha3_512,
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), str(signature).lower())


def mark_successful_opay_payment(order, transaction):
    """Settle only a matching OPay SUCCESS response; repeated checks are safe."""
    if not order or order.payment_method != "opay_checkout" or order.payment_provider != "opay":
        return False, "This transaction is not an OPay hosted-checkout order."
    reference = str(transaction.get("reference") or "")
    if reference != (order.payment_reference or ""):
        logger.warning("OPay reference mismatch for order %s.", order.public_id)
        return False, "The OPay reference does not match this order."
    amount_info = transaction.get("amount") or {}
    raw_amount = amount_info.get("total")
    try:
        amount = int(raw_amount) if raw_amount is not None else None
    except (TypeError, ValueError, AttributeError):
        amount = None
    currency = str(amount_info.get("currency") or "").upper()
    if amount != _expected_amount_kobo(order) or currency != "NGN":
        logger.warning("OPay amount/currency mismatch for order %s.", order.public_id)
        return False, "The OPay amount or currency does not match this order."
    status = str(transaction.get("status") or "").upper()
    if status in {"FAIL", "CLOSE"}:
        order.payment_status = "Failed"
        order.payment_failure_reason = str(transaction.get("failureReason") or "OPay reported an unsuccessful payment.")[:500]
        order.payment_checkout_url = None
        db.session.commit()
        return False, "OPay has not reported a successful payment. Manual OPay transfer remains available."
    if status != "SUCCESS" or transaction.get("isVoided") is True:
        return False, "OPay has not confirmed a successful payment yet."
    if order.payment_status == "Verified":
        return True, "Payment was already verified."

    now = datetime.utcnow()
    channel = str(transaction.get("instrumentType") or transaction.get("channel") or "online")[:30]
    # Claim settlement atomically. A concurrent return/callback can only create
    # the ledger row if it changed this order from unverified to verified.
    claim = db.session.execute(
        update(Order)
        .where(Order.id == order.id, Order.payment_status != "Verified")
        .values(
            payment_status="Verified",
            payment_verified_at=now,
            payment_verified_by_role="opay",
            payment_verified_by_name="OPay",
            payment_channel=channel,
            payment_failure_reason=None,
        )
        .execution_options(synchronize_session=False)
    )
    if int(getattr(claim, "rowcount", 0) or 0) != 1:
        db.session.rollback()
        db.session.refresh(order)
        if order.payment_status == "Verified":
            return True, "Payment was already verified."
        return False, "The order changed while processing; re-check its payment status."

    initial_record = OrderFinancialRecord.query.filter_by(
        order_id=order.id, event_type="initial_payment"
    ).order_by(OrderFinancialRecord.created_at, OrderFinancialRecord.id).first()
    if initial_record is None:
        initial_record = OrderFinancialRecord()
        initial_record.order_id = order.id
        initial_record.event_type = "initial_payment"
        initial_record.amount = order.total
        initial_record.payment_method = "opay checkout"
        initial_record.status = "settled"
        initial_record.reference = reference[:160]
        initial_record.notes = "Payment verified server-side through OPay Cashier status."
        initial_record.settled_at = now
        db.session.add(initial_record)
    else:
        initial_record.status = "settled"
        initial_record.payment_method = "opay checkout"
        initial_record.reference = reference[:160]
        initial_record.notes = "Payment verified server-side through OPay Cashier status."
        initial_record.settled_at = now
    db.session.commit()
    logger.info("OPay payment verified for order %s.", order.public_id)
    return True, "OPay payment verified. The order is ready for owner confirmation."
