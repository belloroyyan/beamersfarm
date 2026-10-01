import hashlib
import hmac
import re
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, jsonify, make_response, redirect, render_template, request, session, url_for

from models import CustomerPushSubscription, DeliveryZone, Order, OrderFinancialRecord, OrderItem, Product, ShopSettings, ShopUpdate, db
from utils.helpers import build_cart
from utils.notifications import normalize_nigerian_phone
from utils.push_subscriptions import valid_push_endpoint
from utils.web_push import send_customer_order_confirmed_push, send_owner_new_order_push, web_push_is_configured

shop_bp = Blueprint("shop", __name__)
PICKUP_ADDRESS = (
    "Beamers Farm, Elapop Estate, Coker Omu Community, along UNIOSUN Main Campus Road, "
    "Oke Baale, Osogbo, Osun State"
)


def customer_notification_key(phone):
    normalized = normalize_nigerian_phone(phone)
    if not normalized:
        normalized = " ".join((phone or "").split()).casefold()
    return hmac.new(
        str(current_app.config["SECRET_KEY"]).encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def current_cart():
    return session.setdefault("cart", {})


def cart_summary(products=None, delivery_fee=None):
    cart = current_cart()
    if products is None:
        ids = [int(key) for key in cart if str(key).isdigit()]
        products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    product_map = {product.id: product for product in products}
    fee = Decimal("0.00") if delivery_fee is None else Decimal(str(delivery_fee))
    summary = build_cart(cart, product_map, fee)
    summary["delivery_fee_selected"] = delivery_fee is not None
    summary["has_weight_priced_items"] = any(
        line["product"].is_weight_priced for line in summary["lines"]
    )
    return summary


def locked_cart_summary(delivery_fee=None):
    cart = current_cart()
    ids = [int(key) for key in cart if str(key).isdigit()]
    if not ids:
        return {"lines": [], "subtotal": Decimal("0.00"), "delivery_fee": Decimal("0.00"), "total": Decimal("0.00")}
    products = db.session.execute(
        db.select(Product).where(Product.id.in_(ids)).with_for_update()
    ).scalars().all()
    return cart_summary(products, delivery_fee=delivery_fee)


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


@shop_bp.get("/help")
def help_page():
    return render_template("help.html")


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
    zones = DeliveryZone.query.filter_by(active=True).order_by(
        DeliveryZone.sort_order.asc(), DeliveryZone.id.asc()
    ).all()
    selected_zone_id = request.values.get("delivery_zone_id", "")
    selected_zone = next((zone for zone in zones if str(zone.id) == selected_zone_id), None)
    summary = cart_summary(delivery_fee=selected_zone.fee if selected_zone else None)

    def render_checkout():
        return render_template(
            "checkout.html", summary=summary, delivery_zones=zones,
            selected_zone_id=selected_zone_id, selected_zone=selected_zone,
        )

    if not summary["lines"]:
        flash("Add at least one product before checking out.", "error")
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        whatsapp_opt_in = request.form.get("whatsapp_opt_in") == "yes"
        if not selected_zone:
            flash("Choose a delivery zone or free farm pickup to see the amount due.", "error")
            return render_checkout()
        if (
            not customer_name or len(customer_name) > 120
            or not phone or len(phone) > 40
            or (not selected_zone.is_pickup and (not address or len(address) > 1000))
        ):
            flash("Please enter a valid name, phone number, and delivery address when delivery is selected.", "error")
            return render_checkout()

        # A fresh transaction plus row locks prevents two workers selling the same stock.
        db.session.rollback()
        try:
            summary = locked_cart_summary(delivery_fee=selected_zone.fee)
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
                address=PICKUP_ADDRESS if selected_zone.is_pickup else address,
                whatsapp_opt_in=whatsapp_opt_in,
                whatsapp_opt_in_at=datetime.utcnow() if whatsapp_opt_in else None,
                status="Received",
                payment_status="Verified" if summary["total"] <= 0 else "Unverified",
                payment_verified_at=datetime.utcnow() if summary["total"] <= 0 else None,
                fulfillment_type="pickup" if selected_zone.is_pickup else "delivery",
                delivery_zone_name=selected_zone.name,
                subtotal=summary["subtotal"],
                delivery_fee=summary["delivery_fee"],
                total=summary["total"],
            )
            db.session.add(order)
            if summary["total"] > 0:
                db.session.add(
                    OrderFinancialRecord(
                        order=order,
                        event_type="initial_payment",
                        amount=summary["total"],
                        status="pending",
                        payment_method="bank transfer",
                        notes="Pay-now amount includes item prices or deposits and the selected delivery fee.",
                    )
                )
            for line in summary["lines"]:
                product = line["product"]
                db.session.add(
                    OrderItem(
                        order=order,
                        product=product,
                        product_name=product.name,
                        quantity=line["quantity"],
                        unit_price=Decimal(str(product.price)),
                        unit=product.unit,
                        pricing_type=product.pricing_type,
                        weight_price_per_kg=product.weight_price_per_kg,
                        subtotal=line["line_subtotal"],
                    )
                )
                product.stock -= line["quantity"]
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        send_owner_new_order_push()
        session["cart"] = {}
        return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))

    return render_checkout()


@shop_bp.get("/order/<string:order_ref>/<string:token>/success")
def order_success(order_ref, token):
    order = Order.query.filter_by(public_id=order_ref, public_token=token).first()
    if order is None and order_ref.isdigit():
        order = Order.query.filter_by(id=int(order_ref), public_token=token).first()
    if order is None:
        from flask import abort
        abort(404)
    return render_template(
        "order_success.html", order=order, push_configured=web_push_is_configured(),
        vapid_public_key=current_app.config.get("VAPID_PUBLIC_KEY", ""),
    )


@shop_bp.get("/order/<string:order_ref>/<string:token>/receipt")
def customer_receipt(order_ref, token):
    order = Order.query.filter_by(public_id=order_ref, public_token=token).first()
    if order is None and order_ref.isdigit():
        order = Order.query.filter_by(id=int(order_ref), public_token=token).first()
    if order is None:
        abort(404)
    return render_template("customer_receipt.html", order=order)


@shop_bp.post("/order/<string:order_ref>/<string:token>/push-subscriptions")
def customer_push_subscription(order_ref, token):
    order = Order.query.filter_by(public_id=order_ref, public_token=token).first()
    if order is None and order_ref.isdigit():
        order = Order.query.filter_by(id=int(order_ref), public_token=token).first()
    if order is None:
        abort(404)
    if not web_push_is_configured():
        return jsonify(error="Push notifications are not configured by the site owner."), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    endpoint = payload.get("endpoint")
    if not valid_push_endpoint(endpoint):
        return jsonify(error="The browser returned an invalid push subscription."), 400
    endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    customer_key = customer_notification_key(order.phone)
    subscription = CustomerPushSubscription.query.filter_by(
        customer_key=customer_key, endpoint_hash=endpoint_hash
    ).first()
    already_linked = bool(
        subscription
        and any(item.id == subscription.id for item in order.customer_push_subscriptions)
    )

    if payload.get("action") == "check":
        if subscription is None:
            return jsonify(enabled=False), 200
        if not already_linked:
            order.customer_push_subscriptions.append(subscription)
            db.session.commit()
            if order.status in {"Confirmed", "Preparing", "Out for delivery", "Delivered", "Ready for pickup", "Picked up"}:
                send_customer_order_confirmed_push(order, subscription_ids=[subscription.id])
        return jsonify(enabled=True, message="Order notifications were already enabled on this device."), 200

    if payload.get("action") != "subscribe":
        return jsonify(error="Choose a valid notification action."), 400
    keys = payload.get("keys")
    p256dh = keys.get("p256dh") if isinstance(keys, dict) else None
    auth = keys.get("auth") if isinstance(keys, dict) else None
    if (
        not isinstance(p256dh, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{40,200}", p256dh)
        or not isinstance(auth, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{16,200}", auth)
    ):
        return jsonify(error="The browser returned an invalid push subscription."), 400

    if subscription is None:
        subscription = CustomerPushSubscription(
            customer_key=customer_key, endpoint_hash=endpoint_hash,
            endpoint=endpoint, p256dh=p256dh, auth=auth
        )
        db.session.add(subscription)
    else:
        subscription.endpoint = endpoint
        subscription.p256dh = p256dh
        subscription.auth = auth
    if not already_linked:
        order.customer_push_subscriptions.append(subscription)
    db.session.commit()
    if not already_linked and order.status in {"Confirmed", "Preparing", "Out for delivery", "Delivered"}:
        send_customer_order_confirmed_push(order, subscription_ids=[subscription.id])
    return jsonify(
        enabled=True,
        message="Order notifications are enabled for this customer on this device. Future orders for this customer will not need another prompt.",
    ), 201
