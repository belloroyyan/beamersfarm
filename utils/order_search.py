"""Shared search predicate for staff order streams."""

from sqlalchemy import or_

from models import Order


def order_search_filter(value):
    term = (value or "").strip()[:120]
    if not term:
        return None
    pattern = f"%{term}%"
    filters = [
        Order.public_id.ilike(pattern),
        Order.customer_name.ilike(pattern),
        Order.phone.ilike(pattern),
    ]
    if term.isdigit():
        filters.append(Order.id == int(term))
    return or_(*filters)
