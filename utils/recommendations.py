from collections import Counter

from models import Order, Product


def personalized_products(customer=None, cart_product_ids=None, limit=4):
    """Return available products ranked from purchase history and owner curation."""
    excluded = {int(value) for value in (cart_product_ids or []) if str(value).isdigit()}
    frequency = Counter()
    if customer:
        for order in Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all():
            for item in order.items:
                if item.product_id:
                    frequency[item.product_id] += 1
    candidates = Product.query.filter(Product.active.is_(True), Product.stock > 0).all()
    scored = []
    for product in candidates:
        if product.id in excluded:
            continue
        score = frequency[product.id] * 100
        if product.recommended:
            score += 35
        if product.featured:
            score += 15
        score += max(0, 10 - product.id / 100000)
        scored.append((score, frequency[product.id], product.created_at, product))
    scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [row[3] for row in scored[:limit]]
