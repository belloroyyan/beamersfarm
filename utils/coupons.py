import secrets
from datetime import datetime

from models import Coupon, Customer, CustomerNotice, db


def gift_coupon_to_customer(template, customer, gift_message=""):
    """Create one unique personal coupon from a shared template, or reuse an existing gift."""
    if not template or not template.active or template.customer_id is not None or not customer or not customer.active:
        return None
    now = datetime.utcnow()
    if (template.starts_at and template.starts_at > now) or (template.ends_at and template.ends_at < now):
        return None
    existing = Coupon.query.filter_by(gift_template_id=template.id, customer_id=customer.id).first()
    if existing:
        return existing
    message = (gift_message or template.gift_message or "").strip()[:500]
    while True:
        suffix = f"-G{customer.id}-{secrets.token_hex(3).upper()}"
        prefix = template.code[:max(1, 40 - len(suffix))].rstrip("-")
        code = f"{prefix}{suffix}"[:40]
        if not Coupon.query.filter_by(code=code).first():
            break
    gift = Coupon(
        code=code,
        discount_type=template.discount_type,
        value=template.value,
        minimum_spend=template.minimum_spend,
        max_uses=1,
        uses=0,
        excluded_product_ids=template.excluded_product_ids,
        active=True,
        starts_at=template.starts_at,
        ends_at=template.ends_at,
        customer_id=customer.id,
        gift_message=message,
        gifted_at=datetime.utcnow(),
        gift_template_id=template.id,
    )
    db.session.add(gift)
    db.session.add(CustomerNotice(
        customer_id=customer.id,
        title="A coupon gift from Beamers Farms",
        message=message or "A personal coupon has been added to your account.",
        kind="coupon",
    ))
    return gift
