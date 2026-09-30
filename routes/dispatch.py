from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import Order
from models import db
from utils.security import is_safe_redirect_url


dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/dispatch")


def rider_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("staff_role") != "dispatch_rider":
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def find_order(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None:
        abort(404)
    return order


@dispatch_bp.get("/")
@rider_required
def dashboard():
    queue = Order.query.filter_by(status="Out for delivery")
    orders = (
        queue
        .order_by(Order.created_at.asc())
        .limit(100)
        .all()
    )
    queue_count = queue.count()
    completed_count = Order.query.filter_by(status="Delivered").count()
    return render_template(
        "dispatch/dashboard.html", orders=orders, queue_count=queue_count,
        completed_count=completed_count,
    )


@dispatch_bp.route("/orders/<string:order_ref>", methods=["GET", "POST"])
@rider_required
def order_detail(order_ref):
    order = find_order(order_ref)
    if order.status == "Delivered":
        flash("This delivery has already been completed.", "success")
        return redirect(url_for("dispatch.dashboard"))
    if order.status != "Out for delivery":
        abort(404)

    if request.method == "POST":
        if order.status != "Out for delivery" or request.form.get("action") != "delivered":
            flash("This delivery cannot be updated from the dispatch desk.", "error")
        else:
            order.status = "Delivered"
            db.session.commit()
            flash("Delivery marked as complete. Thank you.", "success")
        return redirect(url_for("dispatch.dashboard"))

    return render_template("dispatch/order_detail.html", order=order)
