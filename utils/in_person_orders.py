from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from sqlalchemy import func

from models import Order, OrderFinancialRecord, OrderItem, Product, db


def _recorded_at(form):
    raw = (form.get("sold_at_local") or "").strip()
    if not raw:
        return datetime.utcnow()
    try:
        if "T" not in raw:
            raise ValueError
        local_time = datetime.fromisoformat(raw)
        if local_time.tzinfo is None:
            local_time = local_time.replace(
                tzinfo=ZoneInfo(current_app.config.get("BUSINESS_TIME_ZONE", "Africa/Lagos"))
            )
        return local_time.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("Enter a valid sale date and time in the business timezone.") from error


def create_in_person_order(form, actor):
    recorded_at = _recorded_at(form)
    rows = []
    for product in Product.query.filter_by(active=True).order_by(Product.name.asc()).with_for_update().all():
        raw_quantity = (form.get(f"quantity_{product.id}") or "").strip()
        if not raw_quantity:
            continue
        try:
            quantity = Decimal(raw_quantity)
        except Exception as error:
            raise ValueError(f"Enter a valid quantity for {product.name}.") from error
        if quantity <= 0 or (not product.allow_fractional_quantity and quantity != quantity.to_integral_value()):
            raise ValueError(f"Use a positive whole quantity for {product.name}.")
        if quantity > product.stock:
            raise ValueError(f"Not enough stock for {product.name}; only {product.stock:g} remains.")
        rows.append((product, quantity))
    if not rows:
        raise ValueError("Add at least one product to the in-person order.")

    name = (form.get("buyer_name") or "").strip()[:120]
    phone = (form.get("buyer_phone") or "").strip()[:40]
    if not name or not phone:
        count = db.session.query(func.count(Order.id)).filter(Order.order_channel == "in_person").scalar() or 0
        if not name:
            name = f"customer{count + 1}"
    total = sum(
        (Decimal(str(product.price)) * quantity for product, quantity in rows),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    order = Order(
        customer_name=name,
        phone=phone,
        address="In-person sale at farm counter",
        status="Picked up",
        payment_status="Verified",
        payment_method="cash",
        payment_provider="in_person",
        payment_reference=(form.get("payment_reference") or "").strip()[:160],
        fulfillment_type="pickup",
        delivery_zone_name="Farm counter",
        subtotal=total,
        total=total,
        order_channel="in_person",
        recorded_by=actor[:120],
        created_at=recorded_at,
        payment_verified_at=recorded_at,
        payment_verified_by_role="owner" if actor == "Owner" else "salesperson",
        payment_verified_by_name=actor[:120],
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(
        OrderFinancialRecord(
            order=order,
            event_type="initial_payment",
            amount=total,
            status="settled",
            payment_method="cash",
            reference=order.payment_reference or "",
            notes="In-person sale recorded at the farm counter.",
            recorded_by=actor[:120],
            settled_at=recorded_at,
        )
    )
    for product, quantity in rows:
        order.items.append(
            OrderItem(
                product=product,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
                unit=product.unit,
                pricing_type="fixed",
                subtotal=(Decimal(str(product.price)) * quantity).quantize(Decimal("0.01")),
            )
        )
        product.stock -= quantity
    db.session.commit()
    return order
