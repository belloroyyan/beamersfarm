from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from datetime import datetime

from models import Complaint, CustomerNotice, Order, Product, SalespersonAccount, ShopSettings, db
from utils.order_workflow import ORDER_STATUSES, update_order_status
from utils.order_settlement import save_order_weights
from utils.order_search import order_search_filter
from utils.push_subscriptions import delete_staff_push_subscription, save_staff_push_subscription
from utils.salesperson_permissions import get_salesperson_permissions, salesperson_has_permission
from utils.web_push import web_push_is_configured
from utils.in_person_orders import create_in_person_order

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


def permission_required(permission):
    def decorate(view):
        @wraps(view)
        def wrapped(account, *args, **kwargs):
            if not salesperson_has_permission(account, permission):
                abort(403)
            return view(account, *args, **kwargs)
        return wrapped
    return decorate


def find_order(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        abort(404)
    return order


def available_statuses(_order):
    """Show the full operational menu; payment-before-confirmation is enforced server-side."""
    return list(ORDER_STATUSES)


def order_search_for_account(query, account):
    if salesperson_has_permission(account, "view_customer_details"):
        return order_search_filter(query)
    query = (query or "").strip()[:120]
    if not query:
        return None
    if query.isdigit():
        return or_(Order.id == int(query), Order.public_id.ilike(f"%{query}%"))
    return Order.public_id.ilike(f"%{query}%")


@salesperson_bp.get("/")
@salesperson_required
def dashboard(account):
    # The order desk remains available; the view_customer_details capability only
    # controls personal contact fields and name/phone search.
    search_query = request.args.get("q", "").strip()[:120]
    orders_query = Order.query.filter(Order.order_channel != "in_person").order_by(Order.created_at.desc())
    order_filter = order_search_for_account(search_query, account)
    if order_filter is not None:
        orders_query = orders_query.filter(order_filter)
    orders = orders_query.limit(150).all()
    stats = {
        "unverified": Order.query.filter_by(payment_status="Unverified").filter(Order.status != "Cancelled").count(),
        "open": Order.query.filter(Order.status.notin_(["Delivered", "Picked up", "Cancelled"])).count(),
        "pickup": Order.query.filter_by(status="Ready for pickup", fulfillment_type="pickup").count(),
        "delivery": Order.query.filter_by(status="Out for delivery", fulfillment_type="delivery").count(),
    }
    permissions = get_salesperson_permissions(account)
    return render_template(
        "salesperson/dashboard.html",
        account=account,
        orders=orders,
        stats=stats,
        search_query=search_query,
        permissions=permissions,
        push_configured=web_push_is_configured(),
        vapid_public_key=current_app.config.get("VAPID_PUBLIC_KEY", ""),
    )


@salesperson_bp.route("/orders/<string:order_ref>", methods=["GET", "POST"])
@salesperson_required
def order_detail(account, order_ref):
    order = find_order(order_ref)
    permissions = get_salesperson_permissions(account)
    if request.method == "POST":
        if request.form.get("save_weights") == "yes":
            if not permissions["record_weigh_ins"]:
                abort(403)
            ok, message = save_order_weights(
                order,
                request.form,
                recorded_by=account.display_name,
                allowed_statuses={"Confirmed", "Preparing"},
            )
            flash(message, "success" if ok else "error")
            return redirect(url_for("salesperson.order_detail", order_ref=order.public_id))

        # Old browser tabs using the retired verify-only control also confirm;
        # payment verification no longer leaves the order in Received.
        verify_only = False
        verify_and_confirm = (
            request.form.get("verify_and_confirm") == "yes"
            or request.form.get("verify_payment_only") == "yes"
        )
        verify_payment = verify_only or verify_and_confirm
        if verify_payment and not permissions["verify_payments"]:
            abort(403)
        if (verify_and_confirm or not verify_payment) and not permissions["change_order_status"]:
            abort(403)
        if verify_payment and request.form.get("payment_received") != "yes":
            flash("Confirm that the transfer is visible in the business POS/bank account before verifying it.", "error")
            return redirect(url_for("salesperson.order_detail", order_ref=order.public_id))
        ok, message = update_order_status(
            order,
            order.status if verify_only else "Confirmed" if verify_and_confirm else request.form.get("status", ""),
            verify_payment=verify_payment,
            actor="salesperson",
            actor_name=account.display_name,
            verification_reference=request.form.get("verification_reference", ""),
        )
        flash(message, "success" if ok else "error")
        return redirect(url_for("salesperson.order_detail", order_ref=order.public_id))
    return render_template(
        "salesperson/order_detail.html",
        account=account,
        order=order,
        available_statuses=available_statuses(order),
        permissions=permissions,
    )


@salesperson_bp.get("/orders/<string:order_ref>/settlement-receipt")
@salesperson_required
def settlement_receipt(account, order_ref):
    if (
        not salesperson_has_permission(account, "view_customer_details")
        or not salesperson_has_permission(account, "print_customer_receipts")
        or not salesperson_has_permission(account, "view_customer_settlement")
    ):
        abort(403)
    order = find_order(order_ref)
    if (
        order.status == "Cancelled"
        or order.payment_status != "Verified"
        or not order.has_weight_priced_items
        or not order.weights_complete
        or order.weighing_completed_at is None
    ):
        abort(404)
    return render_template("salesperson/settlement_receipt.html", account=account, order=order)


@salesperson_bp.post("/push-subscriptions")
@salesperson_required
def save_push_subscription(account):
    if not salesperson_has_permission(account, "receive_order_alerts"):
        return jsonify(error="The Owner has disabled new-order alerts for this account."), 403
    return save_staff_push_subscription("salesperson", salesperson_account_id=account.id)


@salesperson_bp.delete("/push-subscriptions")
@salesperson_required
def delete_push_subscription(account):
    return delete_staff_push_subscription("salesperson", salesperson_account_id=account.id)


COMPLAINT_STATUSES = ["New", "Under Review", "Resolved", "Closed"]


@salesperson_bp.get("/order-stream")
@salesperson_required
@permission_required("view_order_stream")
def order_stream(account):
    search_query = request.args.get("q", "").strip()[:120]
    sort = request.args.get("sort", "newest")
    sort_column = (
        Order.created_at.asc() if sort == "oldest"
        else Order.total.desc() if sort == "value"
        else Order.created_at.desc()
    )
    query = Order.query.filter(Order.order_channel != "in_person").order_by(sort_column)
    order_filter = order_search_for_account(search_query, account)
    if order_filter is not None:
        query = query.filter(order_filter)
    return render_template(
        "salesperson/order_stream.html",
        account=account,
        orders=query.limit(150).all(),
        search_query=search_query,
        sort=sort,
        permissions=get_salesperson_permissions(account),
        stream_refresh_seconds=20,
    )


@salesperson_bp.get("/complaints")
@salesperson_required
@permission_required("view_complaints")
def complaints(account):
    query_text = request.args.get("q", "").strip()[:120]
    status = request.args.get("status", "").strip()
    complaints_query = Complaint.query.outerjoin(Order, Complaint.order_id == Order.id).options(
        selectinload(Complaint.order)
    ).order_by(Complaint.created_at.desc())
    if status in COMPLAINT_STATUSES:
        complaints_query = complaints_query.filter(Complaint.status == status)
    if query_text:
        terms = [
            Complaint.customer_name.ilike(f"%{query_text}%"),
            Complaint.phone.ilike(f"%{query_text}%"),
            Complaint.subject.ilike(f"%{query_text}%"),
            Complaint.status.ilike(f"%{query_text}%"),
        ]
        if query_text.isdigit():
            terms.extend([Complaint.id == int(query_text), Complaint.order_id == int(query_text), Order.id == int(query_text)])
        terms.append(Order.public_id.ilike(f"%{query_text}%"))
        complaints_query = complaints_query.filter(or_(*terms))
    return render_template(
        "salesperson/complaints.html",
        account=account,
        complaints=complaints_query.limit(200).all(),
        search_query=query_text,
        statuses=COMPLAINT_STATUSES,
        selected_status=status,
        status_counts={item: Complaint.query.filter_by(status=item).count() for item in COMPLAINT_STATUSES},
        permissions=get_salesperson_permissions(account),
    )


@salesperson_bp.route("/complaints/<int:complaint_id>", methods=["GET", "POST"])
@salesperson_required
@permission_required("view_complaints")
def complaint_detail(account, complaint_id):
    complaint = db.session.get(Complaint, complaint_id)
    if complaint is None:
        abort(404)
    permissions = get_salesperson_permissions(account)
    if request.method == "POST":
        # Viewing is one permission; changing a complaint needs its own.
        if not permissions["manage_complaints"]:
            abort(403)
        status = request.form.get("status", "")
        if status not in COMPLAINT_STATUSES:
            flash("Choose a valid complaint status.", "error")
        else:
            previous_state = (complaint.status, complaint.owner_notes)
            complaint.status = status
            complaint.owner_notes = request.form.get("owner_notes", "").strip()[:5000]
            complaint.resolved_at = datetime.utcnow() if status in {"Resolved", "Closed"} else None
            if previous_state != (complaint.status, complaint.owner_notes):
                customer = complaint.order.customer if complaint.order else None
                if customer:
                    public_id = complaint.order.public_id or str(complaint.order.id)
                    db.session.add(CustomerNotice(
                        customer_id=customer.id,
                        title="Your complaint was updated",
                        message=f"Your complaint about order {public_id} has been updated to {complaint.status}.",
                        kind="complaint",
                        created_by=account.display_name[:120],
                    ))
            db.session.commit()
            flash("Complaint updated.", "success")
        return redirect(url_for("salesperson.complaint_detail", complaint_id=complaint.id))
    return render_template(
        "salesperson/complaint_detail.html",
        account=account,
        complaint=complaint,
        statuses=COMPLAINT_STATUSES,
        permissions=permissions,
    )


@salesperson_bp.route("/in-person-orders", methods=["GET","POST"])
@salesperson_required
@permission_required("record_in_person_orders")
def in_person_order(account):
 products=Product.query.filter_by(active=True).order_by(Product.name.asc()).all()
 if request.method=="POST":
  try:o=create_in_person_order(request.form,account.display_name)
  except ValueError as ex: flash(str(ex),"error");return render_template("salesperson/in_person_order.html",account=account,products=products)
  flash(f"In-person order {o.customer_name} recorded in inventory and reports.","success");return redirect(url_for("salesperson.in_person_order"))
 return render_template("salesperson/in_person_order.html",account=account,products=products)

@salesperson_bp.get("/inventory")
@salesperson_required
@permission_required("view_inventory")
def inventory(account):
    products = Product.query.filter_by(active=True).order_by(Product.name.asc()).all()
    return render_template("salesperson/inventory.html", account=account, products=products)
