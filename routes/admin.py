from decimal import Decimal
from functools import wraps

from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models import Complaint, Order, OrderItem, OrderNotification, Product, ShopSettings, ShopUpdate, db
from utils.notifications import build_order_confirmed_message, normalize_nigerian_phone
from utils.product_images import save_product_image
from utils.updates import delete_update_image, save_update_image
from utils.security import is_safe_redirect_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ORDER_STATUSES = ["Received", "Confirmed", "Preparing", "Out for delivery", "Delivered", "Cancelled"]
COMPLAINT_STATUSES = ["New", "Under Review", "Resolved", "Closed"]
COMPLAINT_CATEGORIES = ["Late delivery", "Missing item", "Incorrect item", "Product quality", "Payment issue", "Delivery experience", "Other"]


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


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "owner")
        password = request.form.get("password", "")
        authenticated = (
            valid_admin_password(password) if role == "owner"
            else valid_dispatch_rider_password(password) if role == "dispatch_rider"
            else False
        )
        if authenticated:
            next_url = request.args.get("next")
            session.clear()
            session["staff_role"] = role
            if role == "owner":
                session["admin_logged_in"] = True
                flash("Welcome back. Your order desk is ready.", "success")
                default_endpoint = "admin.dashboard"
                allowed_next = next_url and not next_url.startswith("/dispatch")
            else:
                flash("Welcome. Your dispatch queue is ready.", "success")
                default_endpoint = "dispatch.dashboard"
                allowed_next = next_url and next_url.startswith("/dispatch")
            if allowed_next and is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for(default_endpoint))
        flash("Those sign-in details did not match.", "error")
    return render_template("admin/login.html")


@admin_bp.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("shop.index"))


@admin_bp.get("/")
@admin_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(100).all()
    shop_settings = ShopSettings.query.get(1)
    stats = {
        "open": Order.query.filter(Order.status.notin_(["Delivered", "Cancelled"])).count(),
        "today": Order.query.filter(db.func.date(Order.created_at) == db.func.current_date()).count(),
        "products": Product.query.filter_by(active=True).count(),
        "low_stock": Product.query.filter(Product.active.is_(True), Product.stock <= 5).count(),
        "complaints": Complaint.query.filter(Complaint.status.in_(["New", "Under Review"])).count(),
    }
    return render_template("admin/dashboard.html", orders=orders, stats=stats, statuses=ORDER_STATUSES, shop_settings=shop_settings)


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
        new_status = request.form.get("status", "")
        if new_status not in ORDER_STATUSES:
            flash("Choose a valid order status.", "error")
        elif new_status != order.status:
            previous_status = order.status
            if new_status == "Cancelled" and order.status != "Cancelled":
                for item in order.items:
                    if item.product:
                        item.product.stock += item.quantity
            elif order.status == "Cancelled" and new_status != "Cancelled":
                for item in order.items:
                    if item.product and item.product.stock < item.quantity:
                        flash(f"Not enough stock to reopen {item.product_name}.", "error")
                        return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES)
                for item in order.items:
                    if item.product:
                        item.product.stock -= item.quantity
            order.status = new_status
            if previous_status != "Confirmed" and new_status == "Confirmed" and order.whatsapp_opt_in:
                existing = OrderNotification.query.filter_by(
                    order_id=order.id,
                    channel="whatsapp",
                    event="order_confirmed",
                ).first()
                if existing is None:
                    db.session.add(
                        OrderNotification(
                            order=order,
                            channel="whatsapp",
                            event="order_confirmed",
                            recipient=normalize_nigerian_phone(order.phone),
                            message=build_order_confirmed_message(order),
                            status="pending",
                        )
                    )
            db.session.commit()
            if new_status == "Confirmed" and previous_status != "Confirmed" and order.whatsapp_opt_in:
                flash("Order confirmed. WhatsApp notification queued for the scheduled sender.", "success")
            else:
                flash("Order status updated.", "success")
        return redirect(url_for("admin.order_detail", order_ref=order.public_id))
    return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES)


@admin_bp.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        unit = request.form.get("unit", "per pack").strip() or "per pack"
        try:
            price = Decimal(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except (ValueError, TypeError, ArithmeticError):
            flash("Enter a valid price and whole-number stock amount.", "error")
            return redirect(url_for("admin.products"))
        if not name or len(name) > 120 or price < 0 or price > Decimal("9999999999.99") or stock < 0:
            flash("Enter a valid product name, price, and stock amount.", "error")
        else:
            image_path, image_error = save_product_image(request.files.get("image"))
            if image_error:
                flash(image_error, "error")
                return redirect(url_for("admin.products"))
            db.session.add(Product(name=name, description=description[:2000], price=price, unit=unit[:80], stock=stock, image=image_path or "chicken"))
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
            price = Decimal(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except (ValueError, TypeError, ArithmeticError):
            flash("Enter a valid price and whole-number stock amount.", "error")
            return render_template("admin/product_edit.html", product=product)
        if price < 0 or price > Decimal("9999999999.99") or stock < 0:
            flash("Enter a valid non-negative price and stock amount.", "error")
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
        OrderNotification.query.delete(synchronize_session=False)
        OrderItem.query.delete(synchronize_session=False)
        Order.query.delete(synchronize_session=False)
        cleared.append("orders and delivery records (including their items and WhatsApp logs)")
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
