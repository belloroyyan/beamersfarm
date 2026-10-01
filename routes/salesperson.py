from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import Order, SalespersonAccount, db
from utils.order_workflow import SALESPERSON_STATUSES, update_order_status

salesperson_bp = Blueprint("salesperson", __name__, url_prefix="/sales")


def salesperson_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("staff_role") != "salesperson":
            return redirect(url_for("admin.login", next=request.path))
        account_id = session.get("salesperson_id")
        account = db.session.get(SalespersonAccount, account_id) if account_id else None
        if account is None or not account.active:
            session.clear()
            flash("This salesperson account is no longer active. Contact the owner if you need access.", "error")
            return redirect(url_for("admin.login"))
        return view(account, *args, **kwargs)

    return wrapped


def find_order(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        abort(404)
    return order


def available_statuses(order):
    current = order.status
    possible = [current]
    if order.payment_status == "Verified":
        for status in SALESPERSON_STATUSES.get(current, set()):
            if order.fulfillment_type == "pickup" and status in {"Out for delivery", "Delivered"}:
                continue
            if order.fulfillment_type != "pickup" and status in {"Ready for pickup", "Picked up"}:
                continue
            possible.append(status)
    return [current] + sorted(set(possible) - {current})


@salesperson_bp.get("/")
@salesperson_required
def dashboard(account):
    orders = Order.query.order_by(Order.created_at.desc()).limit(150).all()
    stats = {
        "unverified": Order.query.filter_by(payment_status="Unverified").filter(Order.status != "Cancelled").count(),
        "open": Order.query.filter(Order.status.notin_(["Delivered", "Picked up", "Cancelled"])).count(),
        "pickup": Order.query.filter_by(status="Ready for pickup", fulfillment_type="pickup").count(),
        "delivery": Order.query.filter_by(status="Out for delivery", fulfillment_type="delivery").count(),
    }
    return render_template("salesperson/dashboard.html", account=account, orders=orders, stats=stats)


@salesperson_bp.route("/orders/<string:order_ref>", methods=["GET", "POST"])
@salesperson_required
def order_detail(account, order_ref):
    order = find_order(order_ref)
    if request.method == "POST":
        ok, message = update_order_status(
            order,
            request.form.get("status", ""),
            verify_payment=False,
            actor="salesperson",
        )
        flash(message, "success" if ok else "error")
        return redirect(url_for("salesperson.order_detail", order_ref=order.public_id))
    return render_template(
        "salesperson/order_detail.html",
        account=account,
        order=order,
        available_statuses=available_statuses(order),
    )
