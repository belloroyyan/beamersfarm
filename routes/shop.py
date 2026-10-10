import hashlib
import hmac
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, abort, current_app, flash, jsonify, make_response, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from models import Coupon, Customer, CustomerPushSubscription, DeliveryZone, GalleryImage, Order, OrderFinancialRecord, OrderItem, PartnerListing, Product, SalespersonAccount, ShopSettings, ShopUpdate, WholesaleOrder, WholesaleOrderItem, db
from utils.helpers import build_cart, format_quantity, parse_quantity, product_uses_requested_kg
from utils.notifications import normalize_nigerian_phone
from utils.product_images import product_image_url
from utils.push_subscriptions import valid_push_endpoint
from utils.update_share import render_update_share_image
from utils.web_push import send_customer_order_confirmed_push, send_customer_order_out_for_delivery_push, send_owner_low_stock_push, send_owner_new_order_push, send_owner_wholesale_request_push, send_salesperson_new_order_push, web_push_is_configured

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


def notify_customer_of_current_order_status(order, subscription_id):
    if order.status == "Out for delivery" and order.fulfillment_type == "delivery":
        return send_customer_order_out_for_delivery_push(order, subscription_ids=[subscription_id])
    if order.status in {"Confirmed", "Preparing", "Out for delivery", "Delivered", "Ready for pickup", "Picked up"}:
        return send_customer_order_confirmed_push(order, subscription_ids=[subscription_id])
    return None


def record_event(event_type):
    try:
        from models import AnalyticsEvent
        db.session.add(AnalyticsEvent(event_type=event_type, path=request.path[:255], referrer=request.referrer or "", user_agent=request.user_agent.string[:500], customer_id=session.get("customer_id")))
        db.session.commit()
    except Exception:
        db.session.rollback()

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
    return summary


def coupon_discount(coupon, summary):
    if not coupon or not coupon.active:
        return Decimal("0.00"), "Coupon is not available."
    now = datetime.utcnow()
    if coupon.starts_at and now < coupon.starts_at: return Decimal("0.00"), "Coupon is not active yet."
    if coupon.ends_at and now > coupon.ends_at: return Decimal("0.00"), "Coupon has expired."
    if coupon.max_uses is not None and coupon.uses >= coupon.max_uses: return Decimal("0.00"), "Coupon usage limit has been reached."
    if summary["subtotal"] < coupon.minimum_spend: return Decimal("0.00"), f"This coupon requires a minimum spend of {coupon.minimum_spend}."
    excluded={x.strip() for x in (coupon.excluded_product_ids or "").split(",") if x.strip()}
    eligible=[line for line in summary["lines"] if str(line["product"].id) not in excluded]
    eligible_total=sum((Decimal(str(line["line_subtotal"])) for line in eligible), Decimal("0.00"))
    if not eligible: return Decimal("0.00"), "This coupon excludes every product in your cart."
    discount=(eligible_total * coupon.value / Decimal("100")) if coupon.discount_type == "percent" else min(Decimal(str(coupon.value)), eligible_total)
    return min(discount, summary["subtotal"]), ""

def apply_coupon(summary, code):
    summary["discount"] = Decimal("0.00"); summary["coupon"] = None
    if not code: summary["total"] = summary["subtotal"] + summary["delivery_fee"]; return summary, ""
    coupon=Coupon.query.filter_by(code=code.strip().upper()).first()
    discount, error=coupon_discount(coupon, summary)
    if error: return summary, error
    summary["discount"]=discount; summary["coupon"]=coupon; summary["total"]=max(Decimal("0.00"), summary["subtotal"] + summary["delivery_fee"] - discount)
    return summary, ""


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


def partner_advertisements_query():
    return PartnerListing.query.filter_by(active=True).order_by(
        PartnerListing.sort_order.asc(), PartnerListing.updated_at.desc(), PartnerListing.id.desc()
    ).limit(6)


def public_url(endpoint, **values):
    path = url_for(endpoint, **values)
    origin = current_app.config.get("PUBLIC_ORIGIN", "").rstrip("/")
    return f"{origin}{path}" if origin else url_for(endpoint, _external=True, **values)

def public_asset_url(path):
    origin = current_app.config.get("PUBLIC_ORIGIN", "").rstrip("/")
    return f"{origin}{path}" if origin else request.url_root.rstrip("/") + path

def seo_meta(title, description, endpoint=None, endpoint_values=None, image=None, content_type="website", robots="index,follow,max-image-preview:large", keywords=None):
    canonical = public_url(endpoint, **(endpoint_values or {})) if endpoint else request.base_url
    return {
        "page_title": title,
        "social_title": title,
        "social_description": description,
        "social_url": canonical,
        "canonical_url": canonical,
        "social_image": image or public_asset_url(url_for("static", filename="images/brand-mark.png")),
        "social_type": content_type,
        "meta_robots": robots,
        "meta_keywords": keywords or "frozen chicken Osogbo, fresh chicken Nigeria, Beamers Farm",
    }


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
        **seo_meta("Fresh Frozen Chicken Delivery in Osogbo | Beamers Farm", "Buy fresh, hygienically packaged frozen chicken, whole birds and chicken parts with delivery across Osogbo or farm pickup.", "shop.index", keywords="frozen chicken Osogbo, chicken delivery Osogbo, fresh chicken Nigeria, Beamers Farm"),
        latest_update=latest_update if show_update else None,
        partner_ads=partner_advertisements_query().all(),
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
    return mark_updates_seen(make_response(render_template("updates.html", updates=items, **seo_meta("Beamers Farm Updates | Chicken, Farm & Delivery News", "Read the latest Beamers Farm updates, chicken availability news, farm notes, and delivery information for Osogbo.", "shop.updates", keywords="Beamers Farm updates, chicken availability Osogbo, farm news Nigeria"))))



@shop_bp.get("/updates/<int:update_id>")
def update_detail(update_id):
    update = ShopUpdate.query.get_or_404(update_id)
    description = " ".join((update.body or "").split())
    if len(description) > 220:
        description = description[:217].rsplit(" ", 1)[0] + "…"
    share_image_url = public_url("shop.update_share_image", update_id=update.id)
    return render_template(
        "update_detail.html",
        update=update,
        **seo_meta(f"{update.topic} | Beamers Farm Update", description or "The latest news from Beamers Farm in Osogbo.", "shop.update_detail", {"update_id": update.id}, share_image_url, "article", keywords="Beamers Farm news, chicken farm Osogbo, local food updates"),
        social_image_alt=f"Share card for Beamers Farm update: {update.topic}",
        social_image_width="1200",
        social_image_height="630",
        social_type="article",
        social_card="summary_large_image",
    )


@shop_bp.get("/updates/<int:update_id>/share-image.png")
def update_share_image(update_id):
    update = ShopUpdate.query.get_or_404(update_id)
    response = make_response(render_update_share_image(update))
    response.mimetype = "image/png"
    response.headers["Content-Disposition"] = f'inline; filename="beamers-farm-update-{update.id}.png"'
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400"
    return response


@shop_bp.get("/help")
def help_page():
    return render_template("help.html", **seo_meta("Help & How to Order | Beamers Farm", "Learn how to shop, choose delivery or farm pickup, pay securely, and get help with a Beamers Farm order.", "shop.help_page", keywords="Beamers Farm help, how to order chicken, chicken delivery help Osogbo"))


@shop_bp.route("/track-order", methods=["GET", "POST"])
def track_order():
    """Open one guest order after matching its public reference and phone."""
    if request.method == "POST":
        order_ref = request.form.get("order_ref", "").strip()
        phone = request.form.get("phone", "").strip()
        order = Order.query.filter_by(public_id=order_ref).first()
        if order is None and order_ref.isdigit():
            order = db.session.get(Order, int(order_ref))

        submitted_phone = normalize_nigerian_phone(phone)
        stored_phone = normalize_nigerian_phone(order.phone) if order else ""
        if not order or not submitted_phone or not stored_phone or not hmac.compare_digest(
            submitted_phone, stored_phone
        ):
            flash(
                "We could not verify that order reference and phone combination. Please check both and try again.",
                "error",
            )
            return render_template("track_order.html", order_ref=order_ref, phone=phone, meta_robots="noindex,follow", **seo_meta("Track Your Beamers Farm Order", "Access the latest status of a Beamers Farm order using its reference and phone number.", "shop.track_order", robots="noindex,follow"))

        # The existing success page and receipt remain protected by the order's
        # random public token. Only a successful two-field match reveals it.
        return redirect(
            url_for("shop.order_success", order_ref=order.public_id, token=order.public_token)
        )

    return render_template("track_order.html", order_ref="", phone="", meta_robots="noindex,follow", **seo_meta("Track Your Beamers Farm Order", "Access the latest status of a Beamers Farm order using its reference and phone number.", "shop.track_order", robots="noindex,follow"))


@shop_bp.get("/updates/dismiss")
def dismiss_update():
    return mark_updates_seen(redirect(url_for("shop.index")))


@shop_bp.get("/products")
def products():
    search_query = request.args.get("q", "").strip()[:120]
    products_query = available_products_query()
    if search_query:
        filters = [Product.name.ilike(f"%{search_query}%"), Product.description.ilike(f"%{search_query}%")]
        if search_query.isdigit():
            filters.append(Product.id == int(search_query))
        products_query = products_query.filter(or_(*filters))
    products = products_query.order_by(Product.created_at.asc()).all()
    return render_template(
        "products.html", products=products,
        partner_ads=partner_advertisements_query().all(),
        search_query=search_query,
        **seo_meta("Fresh Frozen Chicken Products in Osogbo | Beamers Farm", "Browse fresh frozen chicken, whole birds and clean chicken portions available for Osogbo delivery or farm pickup.", "shop.products", robots="noindex,follow" if search_query else "index,follow,max-image-preview:large", keywords="buy frozen chicken Osogbo, chicken parts Nigeria, Beamers Farm products"),
    )


@shop_bp.get("/partner-offers/<int:listing_id>")
def partner_offer(listing_id):
    listing = PartnerListing.query.filter_by(id=listing_id, active=True).first_or_404()
    return render_template("partner_offer.html", listing=listing, meta_robots="noindex,follow", **seo_meta(f"{listing.name} | Independent Supplier Offer", (listing.description or "Independent supplier offer from the Beamers Farm marketplace.")[:155], "shop.partner_offer", {"listing_id": listing.id}, robots="noindex,follow"))


@shop_bp.get("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reorder_order = None
    customer = db.session.get(Customer, session.get("customer_id")) if session.get("customer_id") else None
    if customer and customer.active:
        reorder_order = Order.query.filter_by(customer_id=customer.id).join(OrderItem).filter(OrderItem.product_id == product.id).order_by(Order.created_at.desc()).first()
    description = " ".join((product.description or "").split())[:155]
    return render_template("product.html", product=product, reorder_order=reorder_order, **seo_meta(f"{product.name} | Fresh Frozen Chicken in Osogbo", description or f"Buy {product.name} from Beamers Farm with Osogbo delivery or farm pickup.", "shop.product_detail", {"product_id": product.id}, public_asset_url(url_for("static", filename="images/brand-mark.png")), "product", keywords=f"{product.name}, frozen chicken Osogbo, buy chicken Nigeria"))


@shop_bp.get("/gallery")
def gallery():
    images = GalleryImage.query.filter_by(active=True).order_by(
        GalleryImage.sort_order.asc(), GalleryImage.created_at.desc(), GalleryImage.id.desc()
    ).all()
    return render_template("gallery.html", images=images, **seo_meta("Beamers Farm Gallery | Farm & Chicken Preparation in Osogbo", "See Beamers Farm farm moments, chicken preparation, packaging, and local updates from Osogbo.", "shop.gallery", keywords="Beamers Farm gallery, chicken farm Osogbo, chicken preparation Nigeria"))


@shop_bp.route("/wholesale", methods=["GET", "POST"])
def wholesale():
    customer = db.session.get(Customer, session.get("customer_id")) if session.get("customer_id") else None
    products = available_products_query().order_by(Product.name.asc()).all()
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        business = request.form.get("business_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        address = request.form.get("delivery_address", "").strip()
        notes = request.form.get("notes", "").strip()[:3000]
        if not name or not business or not phone or not address:
            flash("Add your name, business name, phone number, and delivery address.", "error")
            return render_template("wholesale.html", products=products, customer=customer, **seo_meta("Wholesale Chicken Orders in Osogbo | Beamers Farm", "Request larger chicken quantities for restaurants, caterers, resellers, and food businesses in Osogbo.", "shop.wholesale", keywords="wholesale chicken Osogbo, bulk chicken Nigeria, restaurant chicken supplier"))
        selected = []
        for product in products:
            raw = request.form.get(f"quantity_{product.id}", "").strip()
            if not raw:
                continue
            try:
                quantity = parse_quantity(raw, allow_fractional=bool(product.allow_fractional_quantity))
            except ValueError:
                flash(f"Enter a valid quantity for {product.name}.", "error")
                return render_template("wholesale.html", products=products, customer=customer, **seo_meta("Wholesale Chicken Orders in Osogbo | Beamers Farm", "Request larger chicken quantities for restaurants, caterers, resellers, and food businesses in Osogbo.", "shop.wholesale", keywords="wholesale chicken Osogbo, bulk chicken Nigeria, restaurant chicken supplier"))
            if quantity > 0:
                selected.append((product, quantity))
        if not selected:
            flash("Choose at least one product quantity for your wholesale request.", "error")
            return render_template("wholesale.html", products=products, customer=customer, **seo_meta("Wholesale Chicken Orders in Osogbo | Beamers Farm", "Request larger chicken quantities for restaurants, caterers, resellers, and food businesses in Osogbo.", "shop.wholesale", keywords="wholesale chicken Osogbo, bulk chicken Nigeria, restaurant chicken supplier"))
        requested_date = None
        if request.form.get("requested_date"):
            try:
                requested_date = datetime.strptime(request.form["requested_date"], "%Y-%m-%d").date()
            except ValueError:
                flash("Choose a valid preferred delivery date.", "error")
                return render_template("wholesale.html", products=products, customer=customer, **seo_meta("Wholesale Chicken Orders in Osogbo | Beamers Farm", "Request larger chicken quantities for restaurants, caterers, resellers, and food businesses in Osogbo.", "shop.wholesale", keywords="wholesale chicken Osogbo, bulk chicken Nigeria, restaurant chicken supplier"))
        order = WholesaleOrder(customer_id=customer.id if customer and customer.active else None, customer_name=name[:120], business_name=business[:160], phone=phone[:40], email=email, delivery_address=address[:2000], requested_date=requested_date, notes=notes)
        db.session.add(order)
        for product, quantity in selected:
            order.items.append(WholesaleOrderItem(product=product, product_name=product.name, quantity=quantity, unit=product.unit))
        db.session.commit()
        send_owner_wholesale_request_push()
        flash(f"Wholesale request {order.public_id} sent. The owner will contact you with pricing and availability.", "success")
        return redirect(url_for("shop.wholesale"))
    return render_template("wholesale.html", products=products, customer=customer, **seo_meta("Wholesale Chicken Orders in Osogbo | Beamers Farm", "Request larger chicken quantities for restaurants, caterers, resellers, and food businesses in Osogbo.", "shop.wholesale", keywords="wholesale chicken Osogbo, bulk chicken Nigeria, restaurant chicken supplier"))


@shop_bp.get("/privacy")
def privacy():
    from models import PrivacyRule
    return render_template("privacy.html", rules=PrivacyRule.query.filter_by(active=True).order_by(PrivacyRule.sort_order.asc(), PrivacyRule.id.asc()).all(), **seo_meta("Privacy & Security | Beamers Farm", "Read the Beamers Farm privacy policy, security information, SSL details, and customer rules.", "shop.privacy", keywords="Beamers Farm privacy policy, chicken shop security, customer data policy"))


@shop_bp.post("/coupon/validate")
def validate_coupon_live():
    code = request.form.get("coupon_code", "").strip().upper()
    zone_id = request.form.get("delivery_zone_id", "")
    zone = DeliveryZone.query.filter_by(id=int(zone_id), active=True).first() if zone_id.isdigit() else None
    summary = cart_summary(delivery_fee=zone.fee if zone else None)
    summary, error = apply_coupon(summary, code)
    if code and not error:
        session["coupon_code"] = code
    elif error:
        session.pop("coupon_code", None)
    return jsonify({
        "ok": not bool(error),
        "code": code,
        "message": error or f"{code} applied.",
        "discount": float(summary.get("discount", Decimal("0.00"))),
        "subtotal": float(summary["subtotal"]),
        "delivery_fee": float(summary["delivery_fee"]),
        "total": float(summary["total"]),
        "delivery_selected": bool(zone),
    })


@shop_bp.get("/robots.txt")
def robots():
    response=make_response(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /checkout\nDisallow: /cart\nDisallow: /track-order\nDisallow: /account\nDisallow: /customer\nSitemap: {public_url('shop.sitemap')}\n", 200)
    response.headers["Content-Type"]="text/plain"
    return response


@shop_bp.get("/google89b2be7fbcad5379.html")
def google_search_console_verification():
    response = make_response("google-site-verification: google89b2be7fbcad5379.html\n", 200)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response

@shop_bp.get("/sitemap.xml")
def sitemap():
    urls=[public_url("shop.index"), public_url("shop.products"), public_url("shop.gallery"), public_url("shop.updates"), public_url("shop.wholesale"), public_url("shop.help_page"), public_url("shop.privacy"), public_url("reviews.testimonials")]
    products=Product.query.filter_by(active=True).all()
    urls += [public_url("shop.product_detail", product_id=p.id) for p in products]
    updates=ShopUpdate.query.order_by(ShopUpdate.created_at.desc()).all()
    urls += [public_url("shop.update_detail", update_id=u.id) for u in updates]
    body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc></url>' for u in urls)+'</urlset>'
    return make_response(body,200,{"Content-Type":"application/xml"})


@shop_bp.get("/cart")
def cart():
    summary=cart_summary()
    customer=db.session.get(Customer, session.get("customer_id")) if session.get("customer_id") else None
    estimate_zone=DeliveryZone.query.filter_by(active=True, is_pickup=False).order_by(DeliveryZone.sort_order.asc()).first() if customer and customer.active else None
    estimate=None
    if customer and customer.active:
        estimate=cart_summary(delivery_fee=estimate_zone.fee if estimate_zone else current_app.config.get("DELIVERY_FEE", 1500))
    return render_template("cart.html", summary=summary, signed_in_customer=customer if customer and customer.active else None, delivery_estimate=estimate, estimate_zone=estimate_zone, **seo_meta("Your Cart | Beamers Farm", "Review your selected Beamers Farm chicken products before choosing delivery or pickup.", "shop.cart", robots="noindex,follow"))


@shop_bp.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    record_event("cart_add")
    product = Product.query.get_or_404(product_id)
    if not product.is_available:
        flash("That product is currently unavailable.", "error")
        return redirect(url_for("shop.index"))
    try:
        quantity = parse_quantity(
            request.form.get("quantity", "1"),
            allow_fractional=bool(product.allow_fractional_quantity),
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(request.referrer or url_for("shop.product_detail", product_id=product.id))
    if quantity > product.stock:
        flash(f"Only {format_quantity(product.stock)} {product.name} unit(s) are available.", "error")
        return redirect(request.referrer or url_for("shop.product_detail", product_id=product.id))
    cart = current_cart()
    key = str(product.id)
    existing = cart.get(key, 0)
    existing_value = existing.get("quantity", 0) if isinstance(existing, dict) else existing
    try:
        existing_quantity = parse_quantity(
            existing_value or "0",
            allow_fractional=bool(product.allow_fractional_quantity),
            allow_zero=True,
        )
    except ValueError:
        existing_quantity = Decimal("0.000")
    new_quantity = existing_quantity + quantity
    if new_quantity > product.stock:
        flash(f"Your cart would exceed the available stock of {product.name}.", "error")
        return redirect(request.referrer or url_for("shop.product_detail", product_id=product.id))
    if product_uses_requested_kg(product):
        try:
            requested_kg = Decimal(request.form.get("requested_weight_kg", ""))
            if not requested_kg.is_finite() or requested_kg < Decimal("0.001") or requested_kg > Decimal("500"):
                raise ValueError
            requested_kg = requested_kg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            previous_kg = Decimal(str(existing.get("requested_weight_kg", "0") or "0")) if isinstance(existing, dict) else Decimal("0")
            combined_kg = (previous_kg + requested_kg).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            if combined_kg > Decimal("500"):
                raise ValueError
        except (InvalidOperation, TypeError, ValueError):
            flash("Enter the combined requested weight for this product in kg (0.001–500 kg).", "error")
            return redirect(request.referrer or url_for("shop.product_detail", product_id=product.id))
        cart[key] = {"quantity": format_quantity(new_quantity), "requested_weight_kg": str(combined_kg)}
    else:
        cart[key] = format_quantity(new_quantity)
    session.modified = True
    flash(f"{product.name} added to your cart.", "success")
    return redirect(request.referrer or url_for("shop.index"))


@shop_bp.post("/cart/update")
def update_cart():
    cart = current_cart()
    updated_cart = {}
    for key in list(cart):
        product = db.session.get(Product, int(key)) if str(key).isdigit() else None
        if not product:
            continue
        try:
            quantity = parse_quantity(
                request.form.get(f"quantity_{key}", "0"),
                allow_fractional=bool(product.allow_fractional_quantity),
                allow_zero=True,
            )
        except ValueError as error:
            flash(f"{product.name}: {error} No cart changes were saved.", "error")
            return redirect(url_for("shop.cart"))
        if quantity <= 0:
            continue
        if quantity > product.stock:
            flash(f"Only {format_quantity(product.stock)} {product.name} unit(s) are available. No cart changes were saved.", "error")
            return redirect(url_for("shop.cart"))
        if product_uses_requested_kg(product):
            try:
                requested_kg = Decimal(request.form.get(f"requested_weight_kg_{key}", ""))
                if not requested_kg.is_finite() or requested_kg < Decimal("0.001") or requested_kg > Decimal("500"):
                    raise ValueError
                requested_kg = requested_kg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            except (InvalidOperation, TypeError, ValueError):
                flash("Enter a valid total requested weight in kg (0.001–500 kg). No cart changes were saved.", "error")
                return redirect(url_for("shop.cart"))
            updated_cart[key] = {"quantity": format_quantity(quantity), "requested_weight_kg": str(requested_kg)}
        else:
            updated_cart[key] = format_quantity(quantity)
    cart.clear()
    cart.update(updated_cart)
    session.modified = True
    flash("Your cart has been updated.", "success")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    current_cart().pop(str(product_id), None)
    session.modified = True
    flash("Item removed from your cart.", "success")
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
    coupon_code = request.values.get("coupon_code", session.get("coupon_code", "")).strip().upper()
    summary, coupon_error = apply_coupon(summary, coupon_code)
    if coupon_code and not coupon_error: session["coupon_code"] = coupon_code
    signed_in_customer = db.session.get(Customer, session.get("customer_id")) if session.get("customer_id") else None

    def render_checkout():
        return render_template(
            "checkout.html", summary=summary, delivery_zones=zones,
            selected_zone_id=selected_zone_id, selected_zone=selected_zone,
            customer=signed_in_customer if signed_in_customer and signed_in_customer.active else None,
            paystack_enabled=current_app.config.get("PAYSTACK_ENABLED", False), coupon_code=coupon_code, coupon_error=coupon_error, **seo_meta("Choose Delivery or Pickup | Beamers Farm", "Choose delivery or free farm pickup for your Beamers Farm order.", "shop.checkout", robots="noindex,follow"),
        )

    if request.method == "GET": record_event("checkout_start")
    if not summary["lines"]:
        flash("Add at least one product before checking out.", "error")
        return redirect(url_for("shop.index"))
    if request.method == "POST":
        if any(line["uses_requested_weight"] and not line["requested_weight_kg"] for line in summary["lines"]):
            flash("Review the quantities in your cart before checkout.", "error")
            return redirect(url_for("shop.cart"))
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        payment_method = request.form.get("payment_method", "bank_transfer")
        address = request.form.get("address", "").strip()
        whatsapp_opt_in = request.form.get("whatsapp_opt_in") == "yes"
        if not selected_zone:
            flash("Choose a delivery zone or free farm pickup to see the amount due.", "error")
            return render_checkout()
        if payment_method not in {"bank_transfer", "paystack"}:
            flash("Choose a valid payment method.", "error")
            return render_checkout()
        if payment_method == "paystack" and not current_app.config.get("PAYSTACK_ENABLED", False):
            flash("Online payment is not enabled yet. Please choose bank transfer.", "error")
            return render_checkout()
        if payment_method == "paystack" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address for online payment, or choose bank transfer.", "error")
            return render_checkout()
        if email and len(email) > 160:
            flash("Enter an email address shorter than 160 characters.", "error")
            return render_checkout()
        if signed_in_customer and normalize_nigerian_phone(phone):
            duplicate_phone = Customer.query.filter(
                Customer.id != signed_in_customer.id,
                Customer.phone == normalize_nigerian_phone(phone),
            ).first()
            duplicate_email = Customer.query.filter(
                Customer.id != signed_in_customer.id,
                Customer.email == email,
            ).first() if email else None
            if duplicate_phone or duplicate_email:
                flash("That phone number or email is already used by another customer account.", "error")
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
            summary, coupon_error = apply_coupon(summary, request.form.get("coupon_code", session.get("coupon_code", "")).strip().upper())
            if coupon_error:
                flash(coupon_error, "error")
                return render_checkout()
            if not summary["lines"]:
                flash("Your cart is empty. Please add a product first.", "error")
                return redirect(url_for("shop.index"))
            for line in summary["lines"]:
                if not line["product"].is_available or line["quantity"] > line["product"].stock:
                    flash(f"Not enough stock for {line['product'].name}. Please update your cart.", "error")
                    return redirect(url_for("shop.cart"))

            order = Order(
                customer_id=signed_in_customer.id if signed_in_customer and signed_in_customer.active else None,
                customer_name=customer_name,
                phone=phone,
                email=email or None,
                address=PICKUP_ADDRESS if selected_zone.is_pickup else address,
                whatsapp_opt_in=whatsapp_opt_in,
                whatsapp_opt_in_at=datetime.utcnow() if whatsapp_opt_in else None,
                status="Received",
                payment_status="Verified" if summary["total"] <= 0 else ("Pending" if payment_method == "paystack" else "Unverified"),
                payment_method=payment_method,
                payment_provider="paystack" if payment_method == "paystack" else "opay",
                payment_verified_at=datetime.utcnow() if summary["total"] <= 0 else None,
                fulfillment_type="pickup" if selected_zone.is_pickup else "delivery",
                delivery_zone_name=selected_zone.name,
                subtotal=summary["subtotal"],
                delivery_fee=summary["delivery_fee"],
                total=summary["total"],
                coupon_code=summary["coupon"].code if summary.get("coupon") else None,
                discount_amount=summary.get("discount", Decimal("0.00")),
            )
            if signed_in_customer and signed_in_customer.active:
                signed_in_customer.name = customer_name
                signed_in_customer.phone = normalize_nigerian_phone(phone) or phone
                signed_in_customer.email = email or signed_in_customer.email
                if not selected_zone.is_pickup:
                    signed_in_customer.address = address
            db.session.add(order)
            if summary.get("coupon"): summary["coupon"].uses += 1
            if summary["total"] > 0:
                db.session.add(
                    OrderFinancialRecord(
                        order=order,
                        event_type="initial_payment",
                        amount=summary["total"],
                        status="pending",
                        payment_method="paystack" if payment_method == "paystack" else "bank transfer",
                        notes="Full order amount due before confirmation, including the selected delivery fee.",
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
                        pricing_type="unit_price",  # New orders use the same ordinary per-unit price for every product.
                        requested_weight_kg=line["requested_weight_kg"],
                        subtotal=line["line_subtotal"],
                    )
                )
                product.stock -= line["quantity"]
            low_stock_products = [line["product"] for line in summary["lines"] if line["product"].stock <= line["product"].low_stock_threshold]
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        send_owner_new_order_push()
        for low_stock_product in low_stock_products:
            send_owner_low_stock_push(low_stock_product)
        if shop_is_open() and SalespersonAccount.query.filter_by(active=True).count():
            send_salesperson_new_order_push()
        session["cart"] = {}
        if payment_method == "paystack":
            return redirect(url_for("payments.start_paystack_payment", order_ref=order.public_id, token=order.public_token))
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
    recommended_products = available_products_query().filter(
        Product.recommended.is_(True)
    ).order_by(Product.created_at.asc()).limit(6).all()
    recommended_partner_listings = PartnerListing.query.filter_by(
        active=True, recommended=True
    ).order_by(PartnerListing.sort_order.asc(), PartnerListing.updated_at.desc()).limit(6).all()
    return render_template(
        "order_success.html", order=order,
        recommended_products=recommended_products,
        recommended_partner_listings=recommended_partner_listings,
        push_configured=web_push_is_configured(),
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
            notify_customer_of_current_order_status(order, subscription.id)
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
    if not already_linked:
        notify_customer_of_current_order_status(order, subscription.id)
    return jsonify(
        enabled=True,
        message="Order notifications are enabled for this customer on this device. Future orders for this customer will not need another prompt.",
    ), 201
