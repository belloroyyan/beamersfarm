import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse
from sqlalchemy import or_

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import Coupon, Customer, CustomerEmailCode, CustomerNotice, CustomerPushSubscription, Order, Product, ShopSettings, WishlistItem, db
from utils.helpers import format_quantity, parse_quantity, product_uses_requested_kg
from utils.notifications import normalize_nigerian_phone
from utils.push_subscriptions import valid_push_endpoint
from utils.recommendations import personalized_products

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
    settings = ShopSettings.query.get(1)
    if settings and not settings.registration_open:
        flash("New customer registration is temporarily closed.", "error")
        return redirect(url_for("customer.login"))
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
                email_verified=False,
            )
            db.session.add(customer)
            db.session.flush()
            now = datetime.utcnow()
            gift_templates = Coupon.query.filter(
                Coupon.active.is_(True), Coupon.customer_id.is_(None),
                Coupon.auto_gift_new_customers.is_(True),
                or_(Coupon.starts_at.is_(None), Coupon.starts_at <= now),
                or_(Coupon.ends_at.is_(None), Coupon.ends_at >= now),
            ).all()
            from utils.coupons import gift_coupon_to_customer
            for template in gift_templates:
                gift_coupon_to_customer(template, customer)
            db.session.commit()
            session["customer_id"] = customer.id
            flash("Your Beamers Farms account is ready.", "success")
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
        matching_customer = Customer.query.filter((Customer.phone == phone) | (Customer.email == identifier)).first() if phone or identifier else None
        if matching_customer and not matching_customer.active:
            flash("This customer account has been deactivated. Please contact Beamers Farms customer care for help.", "error")
        elif not matching_customer or not check_password_hash(matching_customer.password_hash, password):
            flash("The phone/email or password is not correct.", "error")
        else:
            customer = matching_customer
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
    previous_product_ids = []
    for order in orders:
        for item in order.items:
            if item.product_id and item.product_id not in previous_product_ids:
                previous_product_ids.append(item.product_id)
    previous_recommendations = Product.query.filter(Product.id.in_(previous_product_ids), Product.active.is_(True), Product.stock > 0).all() if previous_product_ids else []
    previous_recommendations.sort(key=lambda item: previous_product_ids.index(item.id))
    personalized_recommendations = personalized_products(customer, limit=4)
    account_coupons = Coupon.query.filter_by(customer_id=customer.id).order_by(Coupon.gifted_at.desc(), Coupon.created_at.desc(), Coupon.id.desc()).all()
    now = datetime.utcnow()
    coupon_statuses = {}
    for coupon in account_coupons:
        if not coupon.active:
            status = "Paused"
        elif coupon.max_uses is not None and coupon.uses >= coupon.max_uses:
            status = "Used"
        elif coupon.starts_at and coupon.starts_at > now:
            status = "Not active yet"
        elif coupon.ends_at and coupon.ends_at < now:
            status = "Expired"
        else:
            status = "Available"
        coupon_statuses[coupon.id] = status
    wishlist_count = WishlistItem.query.filter_by(customer_id=customer.id).count()
    from services.email import smtp_is_configured
    return render_template("customer/account.html", customer=customer, orders=orders, previous_recommendations=previous_recommendations[:4], personalized_recommendations=personalized_recommendations, account_coupons=account_coupons, coupon_statuses=coupon_statuses, wishlist_count=wishlist_count, email_verification_ready=smtp_is_configured(), vapid_public_key=current_app.config.get("VAPID_PUBLIC_KEY", ""))


@customer_bp.get("/wishlist")
@account_required
def wishlist():
    customer = current_customer()
    items = WishlistItem.query.filter_by(customer_id=customer.id).order_by(WishlistItem.created_at.desc()).all()
    return render_template("customer/wishlist.html", customer=customer, wishlist_items=items)


@customer_bp.post("/wishlist/<int:product_id>/add")
@account_required
def add_to_wishlist(product_id):
    customer = current_customer()
    product = Product.query.filter_by(id=product_id, active=True).first_or_404()
    item = WishlistItem.query.filter_by(customer_id=customer.id, product_id=product.id).first()
    if item is None:
        db.session.add(WishlistItem(customer_id=customer.id, product_id=product.id))
        db.session.commit()
        flash(f"{product.name} was saved to your wishlist.", "success")
    else:
        flash(f"{product.name} is already in your wishlist.", "success")
    return redirect(safe_next(request.form.get("next")))


@customer_bp.post("/wishlist/<int:product_id>/remove")
@account_required
def remove_from_wishlist(product_id):
    customer = current_customer()
    item = WishlistItem.query.filter_by(customer_id=customer.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("The item was removed from your wishlist.", "success")
    return redirect(safe_next(request.form.get("next") or url_for("customer.wishlist")))


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
    email_changed = customer.email != email
    customer.name, customer.phone, customer.email, customer.address = name, phone, email, address
    if email_changed:
        customer.email_verified = False
        customer.email_verified_at = None
        CustomerEmailCode.query.filter_by(customer_id=customer.id).delete(synchronize_session=False)
    customer.push_notifications_enabled = request.form.get("push_notifications") == "yes"
    customer.whatsapp_notifications_enabled = request.form.get("whatsapp_notifications") == "yes"
    customer.community_profile_public = request.form.get("community_profile_public") == "yes"
    db.session.commit()
    flash("Your account details, notification preferences, and community privacy were saved.", "success")
    return redirect(url_for("customer.account"))


@customer_bp.post("/notices/<int:notice_id>/dismiss")
@account_required
def dismiss_notice(notice_id):
    customer = current_customer()
    notice = CustomerNotice.query.filter_by(
        id=notice_id, customer_id=customer.id, dismissed_at=None
    ).first()
    if notice:
        notice.dismissed_at = datetime.utcnow()
        db.session.commit()
    return redirect(safe_next(request.form.get("next", "")))


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
    from routes.shop import sync_abandoned_cart
    sync_abandoned_cart()
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

@customer_bp.post("/push-subscriptions")
@account_required
def save_account_push_subscription():
    customer = current_customer()
    if not current_app.config.get("VAPID_PUBLIC_KEY"):
        return jsonify(error="Push notifications are not configured by the site owner."), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    endpoint_value = payload.get("endpoint")
    if not isinstance(endpoint_value, str) or not valid_push_endpoint(endpoint_value):
        return jsonify(error="The browser returned an invalid push subscription."), 400
    endpoint = endpoint_value
    import hashlib, hmac, re
    normalized = normalize_nigerian_phone(customer.phone) or customer.phone
    customer_key = hmac.new(str(current_app.config["SECRET_KEY"]).encode(), normalized.encode(), hashlib.sha256).hexdigest()
    endpoint_hash = hashlib.sha256(endpoint.encode()).hexdigest()
    subscription = CustomerPushSubscription.query.filter_by(customer_key=customer_key, endpoint_hash=endpoint_hash).first()
    if subscription is None:
        keys = payload.get("keys") or {}; p256dh, auth = keys.get("p256dh"), keys.get("auth")
        if not isinstance(p256dh, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,200}", p256dh) or not isinstance(auth, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,200}", auth):
            return jsonify(error="The browser returned an invalid push subscription."), 400
        subscription = CustomerPushSubscription(customer_key=customer_key, endpoint_hash=endpoint_hash, endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.session.add(subscription)
    for order in customer.orders:
        if subscription not in order.customer_push_subscriptions: order.customer_push_subscriptions.append(subscription)
    customer.push_notifications_enabled = True
    db.session.commit()
    return jsonify(enabled=True, message="Customer notifications are enabled for updates, gallery posts, community notices, coupons, and order changes."), 201

@customer_bp.post("/send-verification")
@account_required
def send_verification():
    customer = current_customer()
    if customer.email_verified:
        flash("This email address is already verified.", "success")
        return redirect(url_for("customer.account"))
    if not customer.email:
        flash("Add an email address first so we can verify it.", "error")
        return redirect(url_for("customer.account"))
    from services.email import send_email, smtp_is_configured
    if not smtp_is_configured():
        flash("Email verification is not configured yet. Add the business email settings and try again.", "error")
        return redirect(url_for("customer.account"))
    now = datetime.utcnow()
    record = CustomerEmailCode.query.filter_by(customer_id=customer.id).first()
    if record and record.last_sent_at and now - record.last_sent_at < timedelta(seconds=60):
        flash("If your email can receive messages, a verification code has been sent. Please wait before requesting another.", "success")
        return redirect(url_for("customer.account"))
    if record and now - record.request_window_started_at < timedelta(hours=1) and record.requests_in_window >= 5:
        flash("Verification requests are temporarily limited. Please try again later.", "error")
        return redirect(url_for("customer.account"))
    if record is None:
        record = CustomerEmailCode(customer_id=customer.id, code_hash="", expires_at=now)
        db.session.add(record)
        record.requests_in_window = 1
        record.request_window_started_at = now
    elif now - record.request_window_started_at >= timedelta(hours=1):
        record.requests_in_window = 1
        record.request_window_started_at = now
    else:
        record.requests_in_window += 1
    code = f"{secrets.randbelow(1_000_000):06d}"
    record.code_hash = _email_code_hash(customer.id, code)
    record.attempts = 0
    record.created_at = now
    record.last_sent_at = now
    record.expires_at = now + timedelta(minutes=10)
    record.consumed_at = None
    db.session.commit()
    try:
        send_email(
            customer.email,
            "Verify your Beamers Farms account",
            f"Hello {customer.name.split()[0]},\n\nYour Beamers Farms email verification code is {code}. It expires in 10 minutes.\n\nIf you did not request this code, you can ignore this email.",
        )
    except RuntimeError as error:
        record.code_hash = ""
        record.consumed_at = datetime.utcnow()
        db.session.commit()
        flash(str(error), "error")
        return redirect(url_for("customer.account"))
    flash("If your email can receive messages, a six-digit verification code has been sent. It expires in 10 minutes.", "success")
    return redirect(url_for("customer.account"))


def _email_code_hash(customer_id, code):
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    message = f"customer-email-code:{customer_id}:{code}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


@customer_bp.post("/verify-email")
@account_required
def verify_email():
    customer = current_customer()
    code = request.form.get("verification_code", "").strip()
    record = CustomerEmailCode.query.filter_by(customer_id=customer.id).first()
    now = datetime.utcnow()
    if not code.isdigit() or len(code) != 6 or not record or record.consumed_at or record.expires_at < now or record.attempts >= 5:
        flash("That code is invalid or expired. Request a new verification code and try again.", "error")
        return redirect(url_for("customer.account"))
    if not hmac.compare_digest(record.code_hash, _email_code_hash(customer.id, code)):
        record.attempts += 1
        if record.attempts >= 5:
            record.consumed_at = now
            record.code_hash = ""
        db.session.commit()
        flash("That code is invalid or expired. Request a new verification code and try again.", "error")
        return redirect(url_for("customer.account"))
    customer.email_verified = True
    customer.email_verified_at = now
    record.consumed_at = now
    record.code_hash = ""
    db.session.commit()
    flash("Email verified. Your customer account is now verified.", "success")
    return redirect(url_for("customer.account"))
