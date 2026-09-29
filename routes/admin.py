from decimal import Decimal
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models import Order, Product, db
from utils.security import is_safe_redirect_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ORDER_STATUSES = ["Received", "Confirmed", "Preparing", "Out for delivery", "Delivered", "Cancelled"]


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def valid_admin_password(password):
    password_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
    if password_hash:
        return check_password_hash(password_hash, password)
    return not current_app.config["IS_PRODUCTION"] and password == current_app.config["ADMIN_PASSWORD"]


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if valid_admin_password(request.form.get("password", "")):
            next_url = request.args.get("next")
            session.clear()
            session["admin_logged_in"] = True
            flash("Welcome back. Your order desk is ready.", "success")
            if next_url and is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))
        flash("That admin password did not match.", "error")
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
    stats = {
        "open": Order.query.filter(Order.status.notin_(["Delivered", "Cancelled"])).count(),
        "today": Order.query.filter(db.func.date(Order.created_at) == db.func.current_date()).count(),
        "products": Product.query.filter_by(active=True).count(),
        "low_stock": Product.query.filter(Product.active.is_(True), Product.stock <= 5).count(),
    }
    return render_template("admin/dashboard.html", orders=orders, stats=stats, statuses=ORDER_STATUSES)


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
@admin_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == "POST":
        new_status = request.form.get("status", "")
        if new_status not in ORDER_STATUSES:
            flash("Choose a valid order status.", "error")
        elif new_status != order.status:
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
            db.session.commit()
            flash("Order status updated.", "success")
        return redirect(url_for("admin.order_detail", order_id=order.id))
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
            db.session.add(Product(name=name, description=description[:2000], price=price, unit=unit[:80], stock=stock, image="chicken"))
            db.session.commit()
            flash("Product added to the catalog.", "success")
        return redirect(url_for("admin.products"))
    products = Product.query.order_by(Product.active.desc(), Product.name.asc()).all()
    return render_template("admin/products.html", products=products)


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
        db.session.commit()
        flash("Product details saved.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_edit.html", product=product)


@admin_bp.post("/products/<int:product_id>/toggle")
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.active = not product.active
    db.session.commit()
    flash(f"{product.name} is now {'visible in the catalog' if product.active else 'archived from the catalog'}.", "success")
    return redirect(url_for("admin.products"))
