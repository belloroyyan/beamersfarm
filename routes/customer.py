import hmac
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import Customer, Order, Product, db
from utils.helpers import format_quantity, parse_quantity, product_uses_requested_kg
from utils.notifications import normalize_nigerian_phone

customer_bp = Blueprint("customer", __name__, url_prefix="/account")


def current_customer():
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    customer = db.session.get(Customer, customer_id)
    if not customer or not customer.active:
        session.pop("customer_id", None)
        return None
    return customer


def account_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_customer() is None:
            flash("Please sign in to access your customer account.", "error")
            return redirect(url_for("customer.login", next=request.full_path))
        return view(*args, **kwargs)
    return wrapped


def safe_next(value):
    if not value:
        return url_for("customer.account")
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/"):
        return url_for("customer.account")
    return value


@customer_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_customer():
        return redirect(url_for("customer.account"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        normalized_phone = normalize_nigerian_phone(phone)
        if not name or len(name) > 120 or not normalized_phone:
            flash("Enter your full name and a valid Nigerian phone number.", "error")
        elif len(password) < 8:
            flash("Your password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("The passwords do not match.", "error")
        elif email and (len(email) > 160 or "@" not in email):
            flash("Enter a valid email address or leave it blank.", "error")
        elif Customer.query.filter_by(phone=normalized_phone).first():
            flash("An account already exists for that phone number. Please sign in.", "error")
        elif email and Customer.query.filter_by(email=email).first():
            flash("An account already exists for that email address.", "error")
        else:
            customer = Customer(
                name=name, phone=normalized_phone, email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(customer)
            db.session.commit()
            session["customer_id"] = customer.id
            flash("Your Beamers Farm account is ready.", "success")
            return redirect(safe_next(request.args.get("next") or request.form.get("next")))
    return render_template("customer/register.html", next_url=request.args.get("next", ""))


@customer_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_customer():
        return redirect(url_for("customer.account"))
    next_url = request.args.get("next") or request.form.get("next", "")
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        phone = normalize_nigerian_phone(identifier)
        customer = Customer.query.filter(
            (Customer.phone == phone) | (Customer.email == identifier)
        ).filter_by(active=True).first() if phone or identifier else None
        if not customer or not check_password_hash(customer.password_hash, password):
            flash("The phone/email or password is not correct.", "error")
        else:
            session["customer_id"] = customer.id
            flash(f"Welcome back, {customer.name.split()[0]}.", "success")
            return redirect(safe_next(next_url))
    return render_template("customer/login.html", next_url=next_url)


@customer_bp.post("/logout")
def logout():
    session.pop("customer_id", None)
    flash("You have been signed out.", "success")
    return redirect(url_for("shop.index"))


@customer_bp.get("")
@account_required
def account():
    customer = current_customer()
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/account.html", customer=customer, orders=orders)


@customer_bp.post("/settings")
@account_required
def save_settings():
    customer = current_customer()
    name = request.form.get("name", "").strip()
    phone = normalize_nigerian_phone(request.form.get("phone", ""))
    email = request.form.get("email", "").strip().lower() or None
    address = request.form.get("address", "").strip()
    if not name or not phone or len(name) > 120 or len(address) > 1000:
        flash("Enter a name, valid phone number, and a delivery address under 1,000 characters.", "error")
        return redirect(url_for("customer.account"))
    duplicate = Customer.query.filter(Customer.id != customer.id, Customer.phone == phone).first()
    if duplicate:
        flash("That phone number is already connected to another account.", "error")
        return redirect(url_for("customer.account"))
    if email and Customer.query.filter(Customer.id != customer.id, Customer.email == email).first():
        flash("That email address is already connected to another account.", "error")
        return redirect(url_for("customer.account"))
    customer.name, customer.phone, customer.email, customer.address = name, phone, email, address
    customer.push_notifications_enabled = request.form.get("push_notifications") == "yes"
    customer.whatsapp_notifications_enabled = request.form.get("whatsapp_notifications") == "yes"
    db.session.commit()
    flash("Your account details and notification preferences were saved.", "success")
    return redirect(url_for("customer.account"))


@customer_bp.post("/password")
@account_required
def change_password():
    customer = current_customer()
    current = request.form.get("current_password", "")
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    if not check_password_hash(customer.password_hash, current):
        flash("Your current password is not correct.", "error")
    elif len(password) < 8:
        flash("Your new password must be at least 8 characters.", "error")
    elif password != confirm:
        flash("The new passwords do not match.", "error")
    else:
        customer.password_hash = generate_password_hash(password)
        db.session.commit()
        flash("Your password was changed.", "success")
    return redirect(url_for("customer.account"))


@customer_bp.post("/claim-order")
@account_required
def claim_order():
    customer = current_customer()
    order_ref = request.form.get("order_ref", "").strip()
    phone = normalize_nigerian_phone(request.form.get("phone", ""))
    order = Order.query.filter_by(public_id=order_ref).first()
    valid_status = order and order.status in {"Delivered", "Picked up"}
    if not order or order.customer_id or not valid_status or not phone or not hmac.compare_digest(phone, normalize_nigerian_phone(order.phone)):
        flash("Only a delivered or picked-up guest order can be claimed with its matching phone number.", "error")
    else:
        order.customer_id = customer.id
        db.session.commit()
        flash("That previous order is now visible in your account.", "success")
    return redirect(url_for("customer.account"))


@customer_bp.post("/reorder/<int:order_id>")
@account_required
def reorder(order_id):
    customer = current_customer()
    order = Order.query.filter_by(id=order_id, customer_id=customer.id).first_or_404()
    cart = session.setdefault("cart", {})
    added = 0
    for item in order.items:
        product = db.session.get(Product, item.product_id) if item.product_id else None
        if not product or not product.is_available:
            continue
        quantity = min(item.quantity, product.stock)
        if quantity <= 0:
            continue
        value = {"quantity": format_quantity(quantity)}
        if product_uses_requested_kg(product) and item.requested_weight_kg:
            value["requested_weight_kg"] = str(item.requested_weight_kg)
        cart[str(product.id)] = value if isinstance(cart.get(str(product.id)), dict) or product_uses_requested_kg(product) else format_quantity(quantity)
        added += 1
    session.modified = True
    flash(f"{added} available item(s) were added to your cart." if added else "None of those products are currently available.", "success" if added else "error")
    return redirect(url_for("shop.cart"))


@customer_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        phone = normalize_nigerian_phone(request.form.get("phone", ""))
        order_ref = request.form.get("order_ref", "").strip()
        customer = Customer.query.filter_by(phone=phone, active=True).first()
        order = Order.query.filter_by(public_id=order_ref).first()
        if not customer or not order or order.status not in {"Delivered", "Picked up"} or not hmac.compare_digest(phone, normalize_nigerian_phone(order.phone)) or order.customer_id not in {None, customer.id}:
            flash("We could not verify those details. Use the phone number on a delivered or picked-up order.", "error")
        else:
            session["password_reset_customer_id"] = customer.id
            return redirect(url_for("customer.reset_password"))
    return render_template("customer/forgot_password.html")


@customer_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    customer_id = session.get("password_reset_customer_id")
    customer = db.session.get(Customer, customer_id) if customer_id else None
    if not customer or not customer.active:
        flash("Start password recovery again.", "error")
        return redirect(url_for("customer.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8 or password != confirm:
            flash("Use matching passwords of at least 8 characters.", "error")
        else:
            customer.password_hash = generate_password_hash(password)
            db.session.commit()
            session.pop("password_reset_customer_id", None)
            session["customer_id"] = customer.id
            flash("Your password was reset. You are now signed in.", "success")
            return redirect(url_for("customer.account"))
    return render_template("customer/reset_password.html")


@customer_bp.post("/delete")
@account_required
def delete_account():
    customer = current_customer()
    for order in list(customer.orders):
        order.customer_id = None
        order.customer_name = "Deleted customer"
        order.phone = "deleted"
        order.email = None
        order.address = "Personal details removed"
        if order.review:
            order.review.customer_name = "Deleted customer"
            order.review.phone = "deleted"
            order.review.email = None
    customer.name = "Deleted customer"
    customer.phone = f"deleted-{customer.id}"
    customer.email = None
    customer.address = ""
    customer.password_hash = generate_password_hash(__import__("secrets").token_urlsafe(32))
    customer.active = False
    customer.deleted_at = datetime.utcnow()
    db.session.commit()
    session.pop("customer_id", None)
    flash("Your account and personal profile details have been removed. Business records were retained in anonymized form.", "success")
    return redirect(url_for("shop.index"))
