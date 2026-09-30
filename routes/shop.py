from datetime import datetime
from decimal import Decimal

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, session, url_for

from models import Order, OrderItem, Product, ShopSettings, ShopUpdate, db
from utils.helpers import build_cart

shop_bp = Blueprint("shop", __name__)


def current_cart():
    return session.setdefault("cart", {})


def cart_summary(products=None):
    cart = current_cart()
    if products is None:
        ids = [int(key) for key in cart if str(key).isdigit()]
        products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    product_map = {product.id: product for product in products}
    return build_cart(cart, product_map, current_app.config["DELIVERY_FEE"])


def locked_cart_summary():
    cart = current_cart()
    ids = [int(key) for key in cart if str(key).isdigit()]
    if not ids:
        return {"lines": [], "subtotal": Decimal("0.00"), "delivery_fee": Decimal("0.00"), "total": Decimal("0.00")}
    products = db.session.execute(
        db.select(Product).where(Product.id.in_(ids)).with_for_update()
    ).scalars().all()
    return cart_summary(products)


def shop_is_open():
    settings = ShopSettings.query.get(1)
    return settings.is_open if settings else current_app.config["SHOP_OPEN_DEFAULT"]


FEATURED_LIMIT = 3


def available_products_query():
    return Product.query.filter_by(active=True).filter(Product.stock > 0)


@shop_bp.get("/")
def index():
    featured = (
        available_products_query()
        .filter(Product.featured.is_(True))
        .order_by(Product.created_at.asc())
        .limit(FEATURED_LIMIT)
        .all()
    )
    if not featured:
        featured = (
            available_products_query()
            .order_by(Product.created_at.asc())
            .limit(FEATURED_LIMIT)
            .all()
        )
    total_products = available_products_query().count()
    latest_update = ShopUpdate.query.order_by(ShopUpdate.id.desc()).first()
    show_update = bool(latest_update and last_seen_update_id() < latest_update.id)
    return render_template(
        "index.html", products=featured, total_products=total_products,
        latest_update=latest_update if show_update else None,
    )


SEEN_UPDATE_COOKIE = "bf_seen_update"


def last_seen_update_id():
    value = request.cookies.get(SEEN_UPDATE_COOKIE, "0")
    return int(value) if value.isdigit() else 0


def mark_updates_seen(response):
    latest = db.session.query(db.func.max(ShopUpdate.id)).scalar() or 0
    response.set_cookie(SEEN_UPDATE_COOKIE, str(latest), max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=True)
    return response


@shop_bp.get("/updates")
def updates():
    items = ShopUpdate.query.order_by(ShopUpdate.created_at.desc()).all()
    return mark_updates_seen(make_response(render_template("updates.html", updates=items)))


@shop_bp.get("/updates/dismiss")
def dismiss_update():
    return mark_updates_seen(redirect(url_for("shop.index")))


@shop_bp.get("/products")
def products():
    products = available_products_query().order_by(Product.created_at.asc()).all()
    return render_template("products.html", products=products)


@shop_bp.get("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product.html", product=product)


@shop_bp.get("/cart")
def cart():
    return render_template("cart.html", summary=cart_summary())


@shop_bp.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_available:
        flash("That product is currently unavailable.", "error")
        return redirect(url_for("shop.index"))
    try:
        quantity = int(request.form.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, min(quantity, product.stock))
    cart = current_cart()
    new_quantity = int(cart.get(str(product.id), 0)) + quantity
    cart[str(product.id)] = min(new_quantity, product.stock)
    session.modified = True
    flash(f"{product.name} added to your crate.", "success")
    return redirect(request.referrer or url_for("shop.index"))


@shop_bp.post("/cart/update")
def update_cart():
    cart = current_cart()
    for key in list(cart):
        try:
            quantity = int(request.form.get(f"quantity_{key}", 0))
        except (TypeError, ValueError):
            quantity = 0
        product = db.session.get(Product, int(key)) if str(key).isdigit() else None
        if not product or quantity <= 0:
            cart.pop(key, None)
        else:
            cart[key] = min(quantity, product.stock)
    session.modified = True
    flash("Your crate has been updated.", "success")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    current_cart().pop(str(product_id), None)
    session.modified = True
    flash("Item removed from your crate.", "success")
    return redirect(url_for("shop.cart"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not shop_is_open():
        settings = ShopSettings.query.get(1)
        return render_template(
            "shop_closed.html",
            message=settings.closed_message if settings else current_app.config["SHOP_CLOSED_MESSAGE"],
        ), 403
    summary = cart_summary()
    if not summary["lines"]:
        flash("Add at least one product before checking out.", "error")
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        whatsapp_opt_in = request.form.get("whatsapp_opt_in") == "yes"
        if not customer_name or len(customer_name) > 120 or not phone or len(phone) > 40 or not address or len(address) > 1000:
            flash("Please enter a valid name, phone number, and delivery address.", "error")
            return render_template("checkout.html", summary=summary)

        # A fresh transaction plus row locks prevents two workers selling the same stock.
        db.session.rollback()
        try:
            summary = locked_cart_summary()
            if not summary["lines"]:
                flash("Your crate is empty. Please add a product first.", "error")
                return redirect(url_for("shop.index"))
            for line in summary["lines"]:
                if not line["product"].is_available or line["quantity"] > line["product"].stock:
                    flash(f"Not enough stock for {line['product'].name}. Please update your crate.", "error")
                    return redirect(url_for("shop.cart"))

            order = Order(
                customer_name=customer_name,
                phone=phone,
                address=address,
                whatsapp_opt_in=whatsapp_opt_in,
                whatsapp_opt_in_at=datetime.utcnow() if whatsapp_opt_in else None,
                status="Received",
                subtotal=summary["subtotal"],
                delivery_fee=summary["delivery_fee"],
                total=summary["total"],
            )
            db.session.add(order)
            for line in summary["lines"]:
                product = line["product"]
                db.session.add(
                    OrderItem(
                        order=order,
                        product=product,
                        product_name=product.name,
                        quantity=line["quantity"],
                        unit_price=Decimal(str(product.price)),
                        subtotal=line["line_subtotal"],
                    )
                )
                product.stock -= line["quantity"]
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        session["cart"] = {}
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))

    return render_template("checkout.html", summary=summary)


@shop_bp.get("/order/<string:order_ref>/<string:token>/success")
def order_success(order_ref, token):
    order = Order.query.filter_by(public_id=order_ref, public_token=token).first()
    if order is None and order_ref.isdigit():
        order = Order.query.filter_by(id=int(order_ref), public_token=token).first()
    if order is None:
        from flask import abort
        abort(404)
    return render_template("order_success.html", order=order)
