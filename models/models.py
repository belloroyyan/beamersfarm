import secrets
import uuid
from datetime import datetime
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

order_customer_push_subscriptions = db.Table(
    "order_customer_push_subscriptions",
    db.Column("order_id", db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True),
    db.Column("subscription_id", db.Integer, db.ForeignKey("customer_push_subscriptions.id", ondelete="CASCADE"), primary_key=True),
)


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        db.CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    price = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    pricing_type = db.Column(db.String(30), nullable=False, default="fixed", server_default="fixed")
    weight_price_per_kg = db.Column(db.Numeric(12, 2), nullable=True)
    unit = db.Column(db.String(80), nullable=False, default="per pack")
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(80), nullable=False, default="chicken")
    active = db.Column(db.Boolean, nullable=False, default=True)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", back_populates="product")

    @property
    def is_available(self):
        return self.active and self.stock > 0

    @property
    def is_weight_priced(self):
        return self.pricing_type == "weight_deposit"


class ShopSettings(db.Model):
    __tablename__ = "shop_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    is_open = db.Column(db.Boolean, nullable=False, default=True)
    closed_message = db.Column(
        db.String(500), nullable=False,
        default="We are currently closed for orders. You can still browse our products.",
    )
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Complaint(db.Model):
    __tablename__ = "complaints"
    __table_args__ = (
        db.CheckConstraint("length(description) >= 10", name="ck_complaints_description_minimum"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="New")
    owner_notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order", back_populates="complaints")

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    public_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32)
    )
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    address = db.Column(db.Text, nullable=False)
    whatsapp_opt_in = db.Column(db.Boolean, nullable=False, default=False)
    whatsapp_opt_in_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="Received")
    payment_status = db.Column(db.String(30), nullable=False, default="Unverified", server_default="Unverified")
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    delivery_fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "OrderNotification", back_populates="order", cascade="all, delete-orphan"
    )
    complaints = db.relationship("Complaint", back_populates="order")
    customer_push_subscriptions = db.relationship(
        "CustomerPushSubscription",
        secondary=order_customer_push_subscriptions,
        back_populates="orders",
    )

    @property
    def has_weight_priced_items(self):
        return any(item.pricing_type == "weight_deposit" for item in self.items)


class OrderNotification(db.Model):
    __tablename__ = "order_notifications"
    __table_args__ = (
        db.UniqueConstraint("order_id", "channel", "event", name="uq_order_notification_event"),
        db.CheckConstraint("attempts >= 0", name="ck_order_notifications_attempts_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    channel = db.Column(db.String(30), nullable=False, default="whatsapp")
    event = db.Column(db.String(60), nullable=False)
    recipient = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=True)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    provider_message_id = db.Column(db.String(160), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order", back_populates="notifications")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        db.CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
        db.CheckConstraint("subtotal >= 0", name="ck_order_items_subtotal_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    unit = db.Column(db.String(80), nullable=False, default="per pack", server_default="per pack")
    pricing_type = db.Column(db.String(30), nullable=False, default="fixed", server_default="fixed")
    weight_price_per_kg = db.Column(db.Numeric(12, 2), nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")


class ShopUpdate(db.Model):
    __tablename__ = "shop_updates"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(160), nullable=True)
    posted_by = db.Column(db.String(80), nullable=False, default="Admin")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class StaffPushSubscription(db.Model):
    __tablename__ = "staff_push_subscriptions"
    __table_args__ = (
        db.UniqueConstraint("staff_role", "endpoint_hash", name="uq_staff_push_subscriptions_role_endpoint_hash"),
    )

    id = db.Column(db.Integer, primary_key=True)
    staff_role = db.Column(db.String(32), nullable=False)
    endpoint_hash = db.Column(db.String(64), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CustomerPushSubscription(db.Model):
    __tablename__ = "customer_push_subscriptions"
    __table_args__ = (
        db.UniqueConstraint("customer_key", "endpoint_hash", name="uq_customer_push_subscriptions_customer_endpoint"),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_key = db.Column(db.String(64), nullable=False)
    endpoint_hash = db.Column(db.String(64), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    orders = db.relationship(
        "Order",
        secondary=order_customer_push_subscriptions,
        back_populates="customer_push_subscriptions",
    )
