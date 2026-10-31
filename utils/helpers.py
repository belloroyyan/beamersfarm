from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

QUANTITY_STEP = Decimal("0.001")
MAX_QUANTITY = Decimal("999999999.999")


def as_decimal(value):
    return Decimal(str(value or 0))


def local_time(value, fmt="%d %b %Y · %H:%M"):
    """Format stored UTC timestamps in the shop's Osogbo/WAT timezone."""
    if value is None:
        return "—"
    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(ZoneInfo("Africa/Lagos")).strftime(fmt)
    except (AttributeError, TypeError, ValueError):
        return str(value)


def format_currency(value):
    amount = as_decimal(value)
    return f"₦{amount:,.2f}"


def format_quantity(value):
    """Render whole or fractional stock quantities without unnecessary zeroes."""
    try:
        amount = Decimal(str(value or 0))
        if not amount.is_finite():
            return "0"
        amount = amount.quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return "0"
    return format(amount.normalize(), "f")


def parse_quantity(value, *, allow_fractional=False, allow_zero=False):
    """Parse a non-negative quantity (up to three decimal places) without rounding input."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a valid quantity.") from None
    if not amount.is_finite() or amount < 0 or (amount == 0 and not allow_zero) or amount > MAX_QUANTITY:
        raise ValueError("Enter a valid quantity within the allowed range.")
    normalized = amount.quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)
    if normalized != amount:
        raise ValueError("Use no more than three decimal places for a quantity.")
    if not allow_fractional and normalized != normalized.to_integral_value():
        raise ValueError("This product only allows whole-number quantities.")
    return normalized


def delivery_fee_for(subtotal, fee=1500):
    return Decimal(str(fee)) if as_decimal(subtotal) > 0 else Decimal("0.00")


def _cart_quantity(raw_value, allow_fractional=True):
    value = raw_value.get("quantity", 0) if isinstance(raw_value, dict) else raw_value
    try:
        return parse_quantity(value, allow_fractional=allow_fractional, allow_zero=True)
    except ValueError:
        return Decimal("0.000")


def product_uses_requested_kg(product):
    """All catalog products use ordinary listed-price × quantity pricing."""
    return False


def _cart_requested_kg(raw_value):
    """Legacy compatibility only; current catalog items do not use separate kg pricing."""
    if not isinstance(raw_value, dict):
        return Decimal("0.000")
    try:
        value = Decimal(str(raw_value.get("requested_weight_kg", "0") or "0"))
        if not value.is_finite() or value <= 0:
            return Decimal("0.000")
        return value.quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.000")


def cart_count(cart):
    return sum(
        (_cart_quantity(value, allow_fractional=True) for value in (cart or {}).values()),
        Decimal("0.000"),
    )


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
        quantity = _cart_quantity(raw_value, allow_fractional=bool(product.allow_fractional_quantity))
        if quantity <= 0:
            continue
        # Retain the old snapshot field for historical compatibility; new products
        # all use standard listed unit price multiplied by the entered quantity.
        requested_kg = _cart_requested_kg(raw_value) if product_uses_requested_kg(product) else None
        processing_methods = cart_processing_methods(raw_value)
        processing_method = join_processing_methods(processing_methods)
        price_multiplier = requested_kg if requested_kg is not None else quantity
        line_subtotal = (as_decimal(product.price) * price_multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        lines.append({
            "product": product,
            "quantity": quantity,
            "uses_requested_weight": requested_kg is not None,
            "requested_weight_kg": requested_kg,
            "processing_method": processing_method,
            "processing_methods": processing_methods,
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

PROCESSING_SEPARATOR = ", "


def split_processing_methods(value):
    """Turn a stored 'A, B' string back into a list (owner options never contain commas)."""
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def join_processing_methods(methods):
    return PROCESSING_SEPARATOR.join(methods or [])


def cart_processing_methods(raw_value):
    """Read the methods from a cart entry, accepting the old single-string format too."""
    if not isinstance(raw_value, dict):
        return []
    if isinstance(raw_value.get("processing_methods"), list):
        return [str(item).strip() for item in raw_value["processing_methods"] if str(item).strip()]
    return split_processing_methods(raw_value.get("processing_method", ""))


def parse_processing_selection(submitted, product):
    """Validate submitted choices against the product's options.

    Returns the choices in the owner's configured order with duplicates removed.
    Raises ValueError if anything submitted is not a configured option.
    """
    allowed = processing_options(product)
    chosen = {str(item).strip() for item in submitted if str(item).strip()}
    if not chosen.issubset(allowed):
        raise ValueError("Choose valid processing options for this product.")
    return [option for option in allowed if option in chosen]


def processing_options(product):
    import json
    try:
        value = json.loads(product.processing_options or "[]")
        return [str(item).strip()[:120] for item in value if str(item).strip()][:8]
    except (TypeError, ValueError):
        return []
