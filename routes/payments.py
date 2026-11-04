"""OPay hosted-checkout start, return and callback endpoints."""

import json

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, request, url_for

from models import Order
from services.payments import (
    initialize_opay_checkout,
    mark_successful_opay_payment,
    opay_is_configured,
    valid_opay_callback_signature,
    verify_opay_transaction,
)

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


def _find_order(order_ref, token=None):
    query = Order.query.filter_by(public_id=order_ref)
    if token is not None:
        query = query.filter_by(public_token=token)
    return query.first()


def _absolute_public_url(endpoint, **values):
    origin = (current_app.config.get("PUBLIC_ORIGIN") or "").rstrip("/")
    if not origin.startswith("https://"):
        raise RuntimeError("Set the public HTTPS site origin before enabling OPay checkout.")
    return origin + url_for(endpoint, **values)


def _refresh_payment(order):
    if not order.payment_reference or order.payment_method != "opay_checkout":
        return False, "This order has no OPay hosted-checkout reference."
    transaction = verify_opay_transaction(order.payment_reference)
    return mark_successful_opay_payment(order, transaction)


@payments_bp.get("/opay/start/<string:order_ref>/<string:token>")
def start_opay_payment(order_ref, token):
    order = _find_order(order_ref, token)
    if order is None:
        abort(404)
    if order.payment_status == "Verified":
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    if order.payment_method != "opay_checkout":
        flash("This order uses manual OPay transfer. No online checkout is pending.", "error")
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    try:
        checkout_url = initialize_opay_checkout(
            order,
            _absolute_public_url("payments.opay_return", order_ref=order.public_id, token=order.public_token),
            _absolute_public_url("payments.opay_callback"),
            _absolute_public_url("payments.opay_return", order_ref=order.public_id, token=order.public_token),
        )
    except RuntimeError as error:
        flash(str(error), "error")
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    return redirect(checkout_url)


@payments_bp.get("/opay/return/<string:order_ref>/<string:token>")
def opay_return(order_ref, token):
    order = _find_order(order_ref, token)
    if order is None:
        abort(404)
    if order.payment_method == "opay_checkout" and order.payment_status != "Verified":
        try:
            ok, message = _refresh_payment(order)
            if ok:
                flash(message, "success")
            elif order.payment_status != "Failed":
                flash("OPay has not confirmed payment yet. You can refresh this page or use manual OPay transfer.", "error")
        except RuntimeError:
            flash("We could not check OPay just now. Your order remains unverified; please retry or use manual OPay transfer.", "error")
    return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))


@payments_bp.post("/opay/callback")
def opay_callback():
    if not opay_is_configured():
        return jsonify(status=False, message="OPay callbacks are disabled"), 503
    raw_body = request.get_data(cache=True)
    try:
        callback = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return jsonify(status=False, message="Invalid JSON"), 400
    payload = callback.get("payload") if isinstance(callback, dict) else None
    if isinstance(callback, dict) and callback.get("type") != "transaction-status":
        return jsonify(status=False, message="Unsupported callback type"), 400
    if not isinstance(payload, dict) or not valid_opay_callback_signature(payload, callback.get("sha512")):
        return jsonify(status=False, message="Invalid signature"), 401
    if payload.get("refunded") is True:
        # Refund notifications must never be interpreted as a new successful payment.
        return jsonify(status=True, message="Refund notification received; no payment settlement applied."), 200
    reference = str(payload.get("reference") or "")
    order = Order.query.filter_by(payment_reference=reference, payment_method="opay_checkout", payment_provider="opay").first()
    if order is None:
        return jsonify(status=False, message="Unknown payment reference"), 404
    try:
        _refresh_payment(order)
    except RuntimeError:
        # A transient status-query failure should be retried by the provider.
        return jsonify(status=False, message="Could not verify payment status"), 503
    return jsonify(status=True), 200
