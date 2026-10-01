from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def as_decimal(value):
    return Decimal(str(value or 0))


def format_currency(value):
    amount = as_decimal(value)
    return f"₦{amount:,.2f}"


def delivery_fee_for(subtotal, fee=1500):
    return Decimal(str(fee)) if as_decimal(subtotal) > 0 else Decimal("0.00")


def _cart_entry(raw_value):
    if isinstance(raw_value, dict):
        quantity_value = raw_value.get("quantity", 0)
        requested_weight = raw_value.get("requested_weight_kg")
    else:
        # Compatibility with carts created before the combined-kg input existed.
        quantity_value = raw_value
        requested_weight = None
    try:
        quantity = max(0, int(quantity_value))
    except (TypeError, ValueError, OverflowError):
        quantity = 0
    return quantity, requested_weight


def parse_requested_weight(value):
    """Return a positive, bounded total kg amount rounded to 0.001 kg, or None."""
    try:
        weight = Decimal(str(value or "").strip())
        if not weight.is_finite() or weight <= 0 or weight > Decimal("500"):
            return None
        if weight.as_tuple().exponent < -3:
            return None
        return weight.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def cart_count(cart):
    return sum(_cart_entry(quantity)[0] for quantity in (cart or {}).values())


def build_cart(cart, products, delivery_fee=1500):
    lines = []
    subtotal = Decimal("0.00")
    has_invalid_weight = False
    for product_id, raw_value in (cart or {}).items():
        try:
            product = products.get(int(product_id))
        except (TypeError, ValueError):
            product = None
        if not product:
            continue
        quantity, raw_weight = _cart_entry(raw_value)
        if quantity <= 0:
            continue

        requested_weight = None
        needs_weight = bool(getattr(product, "is_sold_by_weight", False))
        if needs_weight:
            requested_weight = parse_requested_weight(raw_weight)
            if requested_weight is None:
                has_invalid_weight = True
                line_subtotal = Decimal("0.00")
            else:
                line_subtotal = (as_decimal(product.price) * requested_weight).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
        else:
            line_subtotal = (as_decimal(product.price) * quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        lines.append(
            {
                "product": product,
                "quantity": quantity,
                "requested_weight_kg": requested_weight,
                "needs_requested_weight": needs_weight and requested_weight is None,
                "line_subtotal": line_subtotal,
            }
        )
        subtotal += line_subtotal

    fee = delivery_fee_for(subtotal, delivery_fee)
    return {
        "lines": lines,
        "subtotal": subtotal,
        "delivery_fee": fee,
        "total": subtotal + fee,
        "has_invalid_weight": has_invalid_weight,
    }
