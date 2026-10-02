from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def as_decimal(value):
    return Decimal(str(value or 0))


def format_currency(value):
    amount = as_decimal(value)
    return f"₦{amount:,.2f}"


def delivery_fee_for(subtotal, fee=1500):
    return Decimal(str(fee)) if as_decimal(subtotal) > 0 else Decimal("0.00")


def _cart_quantity(raw_value):
    value = raw_value.get("quantity", 0) if isinstance(raw_value, dict) else raw_value
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def product_uses_requested_kg(product):
    """All current catalog products use ordinary listed-price × quantity pricing."""
    return False


def _cart_requested_kg(raw_value):
    if not isinstance(raw_value, dict):
        return Decimal("0.000")
    try:
        value = Decimal(str(raw_value.get("requested_weight_kg", "0") or "0"))
        if not value.is_finite() or value <= 0:
            return Decimal("0.000")
        return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.000")


def cart_count(cart):
    return sum(_cart_quantity(value) for value in (cart or {}).values())


def build_cart(cart, products, delivery_fee=1500):
    lines = []
    subtotal = Decimal("0.00")
    for product_id, raw_value in (cart or {}).items():
        try:
            product = products.get(int(product_id))
        except (TypeError, ValueError):
            product = None
        if not product:
            continue
        quantity = _cart_quantity(raw_value)
        if quantity <= 0:
            continue
        requested_kg = _cart_requested_kg(raw_value) if product_uses_requested_kg(product) else None
        price_multiplier = requested_kg if requested_kg is not None else Decimal(quantity)
        line_subtotal = (as_decimal(product.price) * price_multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        lines.append({
            "product": product,
            "quantity": quantity,
            "uses_requested_weight": requested_kg is not None,
            "requested_weight_kg": requested_kg,
            "line_subtotal": line_subtotal,
        })
        subtotal += line_subtotal

    fee = delivery_fee_for(subtotal, delivery_fee)
    return {
        "lines": lines,
        "subtotal": subtotal,
        "delivery_fee": fee,
        "total": subtotal + fee,
    }
