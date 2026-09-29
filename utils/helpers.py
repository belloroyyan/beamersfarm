from decimal import Decimal


def as_decimal(value):
    return Decimal(str(value or 0))


def format_currency(value):
    amount = as_decimal(value)
    return f"₦{amount:,.2f}"


def delivery_fee_for(subtotal, fee=1500):
    return Decimal(str(fee)) if as_decimal(subtotal) > 0 else Decimal("0.00")


def cart_count(cart):
    return sum(int(quantity) for quantity in cart.values())


def build_cart(cart, products, delivery_fee=1500):
    lines = []
    subtotal = Decimal("0.00")
    for product_id, raw_quantity in cart.items():
        product = products.get(int(product_id))
        if not product:
            continue
        quantity = max(0, int(raw_quantity))
        if quantity == 0:
            continue
        line_subtotal = as_decimal(product.price) * quantity
        lines.append(
            {
                "product": product,
                "quantity": quantity,
                "line_subtotal": line_subtotal,
            }
        )
        subtotal += line_subtotal
    fee = delivery_fee_for(subtotal, delivery_fee)
    return {"lines": lines, "subtotal": subtotal, "delivery_fee": fee, "total": subtotal + fee}
