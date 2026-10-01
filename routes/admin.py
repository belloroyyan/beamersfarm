from decimal import Decimal
from functools import wraps

from datetime import datetime
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from models import Complaint, CustomerPushSubscription, DeliveryZone, Order, OrderFinancialRecord, OrderItem, OrderNotification, Product, SalespersonAccount, ShopSettings, ShopUpdate, StaffPushSubscription, db, order_customer_push_subscriptions
from utils.notifications import build_order_confirmed_message, normalize_nigerian_phone
from utils.product_images import save_product_image
from utils.updates import delete_update_image, save_update_image
from utils.security import is_safe_redirect_url
from utils.push_subscriptions import delete_staff_push_subscription, save_staff_push_subscription
from utils.web_push import send_customer_order_confirmed_push, send_dispatch_assignment_push, web_push_is_configured
from utils.order_workflow import ORDER_STATUSES, update_order_status
from utils.order_settlement import save_order_weights

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
COMPLAINT_STATUSES = ["New", "Under Review", "Resolved", "Closed"]
COMPLAINT_CATEGORIES = ["Late delivery", "Missing item", "Incorrect item", "Product quality", "Payment issue", "Delivery experience", "Other"]

MAX_PRODUCT_PRICE = Decimal("9999999999.99")
MAX_DELIVERY_FEE = Decimal("1000000.00")


def parse_product_price_stock(form):
    try:
        price = Decimal(form.get("price", "0"))
        stock = int(form.get("stock", "0"))
        if price < 0 or price > MAX_PRODUCT_PRICE or stock < 0:
            raise ValueError("Enter a valid non-negative price and stock amount.")
    except (ArithmeticError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error):
            raise
        raise ValueError("Enter a valid price and whole-number stock amount.") from error
    return price, stock


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("staff_role") != "owner" and not session.get("admin_logged_in"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def valid_admin_password(password):
    password_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
    if password_hash:
        return check_password_hash(password_hash, password)
    return not current_app.config["IS_PRODUCTION"] and password == current_app.config["ADMIN_PASSWORD"]


def valid_dispatch_rider_password(password):
    password_hash = current_app.config.get("DISPATCH_RIDER_PASSWORD_HASH", "")
    if password_hash:
        return check_password_hash(password_hash, password)
    return (
        not current_app.config["IS_PRODUCTION"]
        and password == current_app.config["DISPATCH_RIDER_PASSWORD"]
    )


def authenticate_salesperson(username, password):
    normalized = (username or "").strip().casefold()
    if not normalized:
        return None
    account = SalespersonAccount.query.filter_by(username=normalized, active=True).first()
    if account and check_password_hash(account.password_hash, password):
        return account
    return None


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    salesperson_account = None
    if request.method == "POST":
        role = request.form.get("role", "owner")
        password = request.form.get("password", "")
        if role == "owner":
            authenticated = valid_admin_password(password)
        elif role == "dispatch_rider":
            authenticated = valid_dispatch_rider_password(password)
        elif role == "salesperson":
            salesperson_account = authenticate_salesperson(request.form.get("username"), password)
            authenticated = salesperson_account is not None
        else:
            authenticated = False
        if authenticated:
            next_url = request.args.get("next")
            session.clear()
            session["staff_role"] = role
            if role == "owner":
                session["admin_logged_in"] = True
                flash("Welcome back. Your order desk is ready.", "success")
                default_endpoint = "admin.dashboard"
                allowed_next = next_url and not next_url.startswith(("/dispatch", "/sales"))
            elif role == "dispatch_rider":
                flash("Welcome. Your dispatch queue is ready.", "success")
                default_endpoint = "dispatch.dashboard"
                allowed_next = next_url and next_url.startswith("/dispatch")
            else:
                session["salesperson_id"] = salesperson_account.id
                session["salesperson_name"] = salesperson_account.display_name
                flash(f"Welcome, {salesperson_account.display_name}. Your sales desk is ready.", "success")
                default_endpoint = "salesperson.dashboard"
                allowed_next = next_url and next_url.startswith("/sales")
            if allowed_next and is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for(default_endpoint))
        flash("Those sign-in details did not match.", "error")
    return render_template(
        "admin/login.html",
        salesperson_enabled=SalespersonAccount.query.filter_by(active=True).count() > 0,
    )


@admin_bp.route("/staff", methods=["GET", "POST"])
@admin_required
def staff_accounts():
    if request.method == "POST":
        action = request.form.get("action", "")
        account_id = request.form.get("account_id", "")
        account = db.session.get(SalespersonAccount, int(account_id)) if account_id.isdigit() else None
        if action == "add":
            display_name = request.form.get("display_name", "").strip()
            username = request.form.get("username", "").strip().casefold()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not display_name or len(display_name) > 120:
                flash("Enter a salesperson name up to 120 characters.", "error")
            elif not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,39}", username):
                flash("Usernames must be 3–40 characters using lowercase letters, numbers, dots, underscores, or hyphens.", "error")
            elif SalespersonAccount.query.filter_by(username=username).first():
                flash("That username is already in use. Re-activate the existing account or choose another username.", "error")
            elif len(password) < 12 or len(password) > 256 or password != confirm:
                flash("Use a password of at least 12 characters and make sure both password fields match.", "error")
            else:
                db.session.add(
                    SalespersonAccount(
                        display_name=display_name,
                        username=username,
                        password_hash=generate_password_hash(password),
                        active=True,
                    )
                )
                db.session.commit()
                flash("Salesperson account created. Share the username and password securely with that employee.", "success")
                return redirect(url_for("admin.staff_accounts"))
        elif action == "reset_password" and account:
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if len(password) < 12 or len(password) > 256 or password != confirm:
                flash("Use a password of at least 12 characters and make sure both password fields match.", "error")
            else:
                account.password_hash = generate_password_hash(password)
                db.session.commit()
                flash(f"Password reset for {account.display_name}.", "success")
                return redirect(url_for("admin.staff_accounts"))
        elif action in {"activate", "deactivate"} and account:
            account.active = action == "activate"
            account.disabled_at = None if account.active else datetime.utcnow()
            db.session.commit()
            flash(
                f"{account.display_name} can now sign in." if account.active
                else f"{account.display_name} access revoked. Active sessions will be rejected on their next request.",
                "success",
            )
            return redirect(url_for("admin.staff_accounts"))
        else:
            flash("Choose a valid salesperson account action.", "error")
        return redirect(url_for("admin.staff_accounts"))
    accounts = SalespersonAccount.query.order_by(SalespersonAccount.active.desc(), SalespersonAccount.display_name.asc()).all()
    return render_template("admin/staff_accounts.html", accounts=accounts)


@admin_bp.post("/logout")
def logout():
    staff_role = session.get("staff_role")
    if staff_role == "dispatch_rider":
        endpoint_hash = session.get("staff_push_subscription_hash") or session.get("dispatch_push_subscription_hash")
        if endpoint_hash:
            try:
                subscription = StaffPushSubscription.query.filter_by(
                    staff_role=staff_role, endpoint_hash=endpoint_hash
                ).first()
                if subscription is not None:
                    db.session.delete(subscription)
                    db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("shop.index"))


@admin_bp.post("/push-subscriptions")
@admin_required
def save_owner_push_subscription():
    return save_staff_push_subscription("owner")


@admin_bp.delete("/push-subscriptions")
@admin_required
def delete_owner_push_subscription():
    return delete_staff_push_subscription("owner")


@admin_bp.get("/")
@admin_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(100).all()
    shop_settings = ShopSettings.query.get(1)
    stats = {
        "open": Order.query.filter(Order.status.notin_(["Delivered", "Picked up", "Cancelled"])).count(),
        "today": Order.query.filter(db.func.date(Order.created_at) == db.func.current_date()).count(),
        "products": Product.query.filter_by(active=True).count(),
        "low_stock": Product.query.filter(Product.active.is_(True), Product.stock <= 5).count(),
        "complaints": Complaint.query.filter(Complaint.status.in_(["New", "Under Review"])).count(),
    }
    return render_template(
        "admin/dashboard.html", orders=orders, stats=stats, statuses=ORDER_STATUSES,
        shop_settings=shop_settings, push_configured=web_push_is_configured(),
        vapid_public_key=current_app.config.get("VAPID_PUBLIC_KEY", ""),
    )


@admin_bp.post("/shop/toggle")
@admin_required
def toggle_shop():
    settings = ShopSettings.query.get(1)
    if not settings:
        settings = ShopSettings(id=1, is_open=current_app.config["SHOP_OPEN_DEFAULT"], closed_message=current_app.config["SHOP_CLOSED_MESSAGE"])
        db.session.add(settings)
    settings.is_open = not settings.is_open
    db.session.commit()
    flash(f"Shop is now {'open for orders' if settings.is_open else 'closed for new orders'}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/orders/<string:order_ref>", methods=["GET", "POST"])
@admin_required
def order_detail(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        from flask import abort
        abort(404)
    if request.method == "POST":
        verify_only = request.form.get("verify_payment_only") == "yes"
        ok, message = update_order_status(
            order,
            order.status if verify_only else request.form.get("status", ""),
            verify_payment=verify_only or request.form.get("verify_payment") == "yes",
            actor="owner",
        )
        flash(message, "success" if ok else "error")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES)


@admin_bp.get("/orders/<string:order_ref>/receipt")
@admin_required
def owner_order_receipt(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        from flask import abort
        abort(404)
    return render_template("admin/owner_receipt.html", order=order)


@admin_bp.post("/orders/<string:order_ref>/weights")
@admin_required
def record_order_weights(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        from flask import abort
        abort(404)
    ok, message = save_order_weights(order, request.form, recorded_by="Owner")
    flash(message, "success" if ok else "error")
    return redirect(url_for("admin.order_detail", order_ref=order.public_id))


@admin_bp.post("/orders/<string:order_ref>/settlements")
@admin_required
def record_order_settlement(order_ref):
    order = Order.query.filter_by(public_id=order_ref).first()
    if order is None and order_ref.isdigit():
        order = db.session.get(Order, int(order_ref))
    if order is None:
        from flask import abort
        abort(404)
    event_type = request.form.get("event_type", "")
    method = request.form.get("payment_method", "")
    reference = request.form.get("reference", "").strip()
    notes = request.form.get("notes", "").strip()
    if event_type not in {"balance_payment", "refund"} or method not in {"cash", "bank transfer"}:
        flash("Choose a valid settlement type and method.", "error")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    if order.payment_status != "Verified" or order.final_total is None:
        flash("Verify the initial payment and record every measured weight before settling a balance or refund.", "error")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    try:
        amount = Decimal(request.form.get("amount", "0"))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99"):
            raise ValueError
        amount = amount.quantize(Decimal("0.01"))
    except (ArithmeticError, TypeError, ValueError):
        flash("Enter a valid settlement amount greater than zero.", "error")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    remaining = order.balance_due if event_type == "balance_payment" else order.refund_due
    if remaining is None or remaining <= 0 or amount > remaining:
        flash("That amount is greater than the currently outstanding balance or refund.", "error")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    now = datetime.utcnow()
    db.session.add(
        OrderFinancialRecord(
            order=order,
            event_type=event_type,
            amount=amount,
            status="settled",
            payment_method=method,
            reference=reference[:160],
            notes=notes[:500],
            recorded_by="Owner",
            created_at=now,
            settled_at=now,
        )
    )
    db.session.commit()
    flash("Financial settlement recorded in the order history.", "success")
    return redirect(url_for("admin.order_detail", order_ref=order.public_id))


@admin_bp.route("/delivery-zones", methods=["GET", "POST"])
@admin_required
def delivery_zones():
    if request.method == "POST":
        action = request.form.get("action", "add")
        zone_id = request.form.get("zone_id", "")
        zone = db.session.get(DeliveryZone, int(zone_id)) if zone_id.isdigit() else None
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name or len(name) > 100 or len(description) > 240:
            flash("Enter a zone name up to 100 characters and an optional description up to 240 characters.", "error")
            return redirect(url_for("admin.delivery_zones"))
        duplicate = DeliveryZone.query.filter(DeliveryZone.name == name)
        if zone:
            duplicate = duplicate.filter(DeliveryZone.id != zone.id)
        if duplicate.first():
            flash("A delivery option with that name already exists.", "error")
            return redirect(url_for("admin.delivery_zones"))
        try:
            fee = Decimal("0.00") if zone and zone.is_pickup else Decimal(request.form.get("fee", "0"))
            if not fee.is_finite() or fee < 0 or fee > MAX_DELIVERY_FEE:
                raise ValueError
        except (ArithmeticError, TypeError, ValueError):
            flash("Enter a valid non-negative fee up to ₦1,000,000.", "error")
            return redirect(url_for("admin.delivery_zones"))
        if action == "update" and zone:
            zone.name = name
            zone.description = description
            zone.fee = fee
            flash("Delivery option updated. Existing orders keep their saved zone and fee.", "success")
        elif action == "add":
            db.session.add(
                DeliveryZone(
                    name=name,
                    description=description,
                    fee=fee,
                    is_pickup=False,
                    active=True,
                    sort_order=(db.session.query(db.func.max(DeliveryZone.sort_order)).scalar() or 0) + 10,
                )
            )
            flash("Delivery zone added and available at checkout.", "success")
        else:
            flash("Choose an existing delivery option to update.", "error")
            return redirect(url_for("admin.delivery_zones"))
        db.session.commit()
        return redirect(url_for("admin.delivery_zones"))
    zones = DeliveryZone.query.order_by(DeliveryZone.sort_order.asc(), DeliveryZone.id.asc()).all()
    return render_template("admin/delivery_zones.html", zones=zones)


@admin_bp.post("/delivery-zones/<int:zone_id>/toggle")
@admin_required
def toggle_delivery_zone(zone_id):
    zone = db.session.get(DeliveryZone, zone_id)
    if zone is None:
        from flask import abort
        abort(404)
    if zone.is_pickup:
        flash("The free farm-pickup option must remain available.", "error")
    else:
        zone.active = not zone.active
        db.session.commit()
        flash(f"{zone.name} is now {'available' if zone.active else 'hidden'} at checkout. Existing orders are unchanged.", "success")
    return redirect(url_for("admin.delivery_zones"))


@admin_bp.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        unit = request.form.get("unit", "per pack").strip() or "per pack"
        try:
            price, stock = parse_product_price_stock(request.form)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin.products"))
        if not name or len(name) > 120:
            flash("Enter a valid product name.", "error")
        else:
            image_path, image_error = save_product_image(request.files.get("image"))
            if image_error:
                flash(image_error, "error")
                return redirect(url_for("admin.products"))
            db.session.add(Product(
                name=name,
                description=description[:2000],
                price=price,
                unit=unit[:80],
                stock=stock,
                image=image_path or "chicken",
            ))
            db.session.commit()
            flash("Product added to the catalog.", "success")
        return redirect(url_for("admin.products"))
    products = Product.query.order_by(Product.active.desc(), Product.name.asc()).all()
    featured_count = sum(1 for product in products if product.featured)
    return render_template(
        "admin/products.html",
        products=products,
        featured_count=featured_count,
        featured_limit=FEATURED_LIMIT,
    )


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        try:
            price, stock = parse_product_price_stock(request.form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("admin/product_edit.html", product=product)
        product.price = price
        product.stock = stock
        product.name = request.form.get("name", "").strip()[:120] or product.name
        product.description = request.form.get("description", "").strip()[:2000]
        product.unit = request.form.get("unit", "per pack").strip()[:80] or "per pack"
        image_path, image_error = save_product_image(request.files.get("image"))
        if image_error:
            flash(image_error, "error")
            return render_template("admin/product_edit.html", product=product)
        if image_path:
            product.image = image_path
        db.session.commit()
        flash("Product details saved.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_edit.html", product=product)


@admin_bp.post("/products/<int:product_id>/toggle")
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.active = not product.active
    if not product.active:
        product.featured = False
    db.session.commit()
    flash(f"{product.name} is now {'visible in the catalog' if product.active else 'archived from the catalog'}.", "success")
    return redirect(url_for("admin.products"))


FEATURED_LIMIT = 3


@admin_bp.post("/products/<int:product_id>/feature")
@admin_required
def toggle_featured(product_id):
    product = Product.query.get_or_404(product_id)
    if product.featured:
        product.featured = False
        db.session.commit()
        flash(f"{product.name} removed from the homepage quick menu.", "success")
        return redirect(url_for("admin.products"))
    if not product.active:
        flash("Restore the product before showing it on the homepage.", "error")
        return redirect(url_for("admin.products"))
    featured_count = Product.query.filter_by(featured=True).count()
    if featured_count >= FEATURED_LIMIT:
        flash(
            f"You can only pin {FEATURED_LIMIT} products to the homepage. Remove one first.",
            "error",
        )
        return redirect(url_for("admin.products"))
    product.featured = True
    db.session.commit()
    flash(f"{product.name} now shows on the homepage quick menu.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.get("/complaints")
@admin_required
def complaints():
    status = request.args.get("status", "").strip()
    query = Complaint.query.order_by(Complaint.created_at.desc())
    if status in COMPLAINT_STATUSES:
        query = query.filter_by(status=status)
    return render_template("admin/complaints.html", complaints=query.all(), statuses=COMPLAINT_STATUSES, selected_status=status)


@admin_bp.route("/complaints/<int:complaint_id>", methods=["GET", "POST"])
@admin_required
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    if request.method == "POST":
        status = request.form.get("status", "")
        if status not in COMPLAINT_STATUSES:
            flash("Choose a valid complaint status.", "error")
        else:
            complaint.status = status
            complaint.owner_notes = request.form.get("owner_notes", "").strip()[:5000]
            complaint.resolved_at = datetime.utcnow() if status in {"Resolved", "Closed"} else None
            db.session.commit()
            flash("Complaint updated.", "success")
        return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))
    return render_template("admin/complaint_detail.html", complaint=complaint, statuses=COMPLAINT_STATUSES)


@admin_bp.route("/updates", methods=["GET", "POST"])
@admin_required
def updates():
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        body = request.form.get("body", "").strip()
        posted_by = request.form.get("posted_by", "").strip() or "Admin"
        if not topic or not body:
            flash("Please add a topic and a message.", "error")
            return render_template("admin/updates.html", updates=ShopUpdate.query.order_by(ShopUpdate.created_at.desc()).all())
        image, error = save_update_image(request.files.get("image"))
        if error:
            flash(error, "error")
            return render_template("admin/updates.html", updates=ShopUpdate.query.order_by(ShopUpdate.created_at.desc()).all())
        db.session.add(ShopUpdate(topic=topic[:160], body=body, image=image, posted_by=posted_by[:80]))
        db.session.commit()
        flash("Update posted. Visitors will see it on the homepage.", "success")
        return redirect(url_for("admin.updates"))
    return render_template("admin/updates.html", updates=ShopUpdate.query.order_by(ShopUpdate.created_at.desc()).all())


@admin_bp.post("/updates/<int:update_id>/delete")
@admin_required
def delete_update(update_id):
    item = ShopUpdate.query.get_or_404(update_id)
    delete_update_image(item.image)
    db.session.delete(item)
    db.session.commit()
    flash("Update deleted.", "success")
    return redirect(url_for("admin.updates"))


@admin_bp.post("/clear-database")
@admin_required
def clear_database():
    """Clear explicitly selected customer/shop activity while keeping app-critical records."""
    if request.form.get("confirm", "").strip().upper() != "CLEAR":
        flash('Nothing was deleted. Type CLEAR in the box to confirm.', "error")
        return redirect(url_for("admin.dashboard"))

    clear_orders = request.form.get("clear_orders") == "yes"
    clear_complaints = request.form.get("clear_complaints") == "yes"
    clear_messages = request.form.get("clear_messages") == "yes"
    clear_updates = request.form.get("clear_updates") == "yes"
    reset_pins = request.form.get("reset_pins") == "yes"
    if not any((clear_orders, clear_complaints, clear_messages, clear_updates, reset_pins)):
        flash("Choose at least one data category or homepage option to clear.", "error")
        return redirect(url_for("admin.dashboard"))

    cleared = []
    if clear_orders:
        # Preserve complaint records even when their related order is removed.
        Complaint.query.filter(Complaint.order_id.isnot(None)).update(
            {Complaint.order_id: None}, synchronize_session=False
        )
        # Keep device opt-in, but remove links to the deleted orders.
        db.session.execute(order_customer_push_subscriptions.delete())
        CustomerPushSubscription.query.delete(synchronize_session=False)
        OrderNotification.query.delete(synchronize_session=False)
        OrderFinancialRecord.query.delete(synchronize_session=False)
        OrderItem.query.delete(synchronize_session=False)
        Order.query.delete(synchronize_session=False)
        cleared.append("orders and delivery records (including items, payment/refund history, WhatsApp logs, and customer push subscriptions)")
    elif clear_messages:
        OrderNotification.query.delete(synchronize_session=False)
        cleared.append("WhatsApp message logs")

    if clear_complaints:
        Complaint.query.delete(synchronize_session=False)
        cleared.append("complaints")
    elif clear_orders:
        cleared.append("complaint records retained with order links removed")

    if clear_updates:
        for item in ShopUpdate.query.all():
            delete_update_image(item.image)
        ShopUpdate.query.delete(synchronize_session=False)
        cleared.append("shop updates")

    if reset_pins:
        Product.query.update({Product.featured: False}, synchronize_session=False)
        cleared.append("homepage product pins")
    db.session.commit()
    flash(
        "Cleared: " + "; ".join(cleared) + ". Products, stock, and shop settings were kept.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))
