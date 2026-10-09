"""Paystack hosted checkout and webhook endpoints."""

import json

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, request, url_for

from models import Order
from services.payments import (
    initialize_paystack_transaction,
    mark_successful_paystack_payment,
    paystack_is_configured,
    valid_webhook_signature,
    verify_paystack_transaction,
)

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


def _find_order(order_ref, token=None):
    query = Order.query.filter_by(public_id=order_ref)
    if token is not None:
        query = query.filter_by(public_token=token)
    return query.first()


@payments_bp.get("/paystack/start/<string:order_ref>/<string:token>")
def start_paystack_payment(order_ref, token):
    order = _find_order(order_ref, token)
    if order is None:
        abort(404)
    if order.payment_status == "Verified":
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    if not order.email:
        flash("An email address is required for online payment. Please use bank transfer or contact Beamers Farm.", "error")
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    try:
        authorization_url = initialize_paystack_transaction(
            order,
            url_for("payments.paystack_callback", _external=True),
        )
    except RuntimeError as error:
        order.payment_status = "Failed"
        order.payment_failure_reason = str(error)[:500]
        from models import db
        db.session.commit()
        flash(str(error), "error")
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
    return redirect(authorization_url)


@payments_bp.get("/paystack/callback")
def paystack_callback():
    reference = request.args.get("trxref") or request.args.get("reference", "")
    if not reference:
        flash("Paystack did not return a payment reference. You can still use bank transfer.", "error")
        return redirect(url_for("shop.index"))
    order = Order.query.filter_by(payment_reference=reference, payment_method="paystack").first()
    if order is None:
        abort(404)
    try:
        response = verify_paystack_transaction(reference)
        transaction = response.get("data", {}) if response.get("status") else {}
        ok, message = mark_successful_paystack_payment(order, transaction)
    except RuntimeError as error:
        ok, message = False, str(error)
    flash(message, "success" if ok else "error")
    return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))


@payments_bp.post("/paystack/webhook")
def paystack_webhook():
    raw_body = request.get_data(cache=True)
    signature = request.headers.get("x-paystack-signature", "")
    if not paystack_is_configured() or not valid_webhook_signature(raw_body, signature):
        return jsonify(status=False, message="Invalid signature"), 401
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return jsonify(status=False, message="Invalid JSON"), 400
    if payload.get("event") == "charge.success":
        data = payload.get("data") or {}
        reference = str(data.get("reference") or "")
        order = Order.query.filter_by(payment_reference=reference, payment_method="paystack").first()
        if order is not None:
            mark_successful_paystack_payment(order, data)
    return jsonify(status=True), 200
