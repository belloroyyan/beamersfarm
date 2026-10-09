import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

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
    unit = db.Column(db.String(80), nullable=False, default="per pack")
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(80), nullable=False, default="chicken")
    active = db.Column(db.Boolean, nullable=False, default=True)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    recommended = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", back_populates="product")

    @property
    def is_available(self):
        return self.active and self.stock > 0

class DeliveryZone(db.Model):
    __tablename__ = "delivery_zones"
    __table_args__ = (
        db.CheckConstraint("fee >= 0", name="ck_delivery_zones_fee_nonnegative"),
        db.UniqueConstraint("name", name="uq_delivery_zones_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(240), nullable=False, default="")
    fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    is_pickup = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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
    email = db.Column(db.String(160), nullable=True)
    whatsapp_opt_in = db.Column(db.Boolean, nullable=False, default=False)
    whatsapp_opt_in_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="Received")
    payment_status = db.Column(db.String(30), nullable=False, default="Unverified", server_default="Unverified")
    payment_method = db.Column(db.String(30), nullable=False, default="bank_transfer", server_default="bank_transfer")
    payment_provider = db.Column(db.String(30), nullable=True)
    payment_reference = db.Column(db.String(160), nullable=True, index=True)
    payment_channel = db.Column(db.String(30), nullable=True)
    payment_initiated_at = db.Column(db.DateTime, nullable=True)
    payment_failure_reason = db.Column(db.String(500), nullable=True)
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    payment_verified_by_role = db.Column(db.String(20), nullable=True)
    payment_verified_by_name = db.Column(db.String(120), nullable=True)
    fulfillment_type = db.Column(db.String(20), nullable=False, default="delivery", server_default="delivery")
    delivery_zone_name = db.Column(db.String(100), nullable=False, default="Pre-zone delivery", server_default="Pre-zone delivery")
    weighing_completed_at = db.Column(db.DateTime, nullable=True)
    weighing_recorded_by = db.Column(db.String(120), nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    delivery_fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    financial_records = db.relationship(
        "OrderFinancialRecord", back_populates="order", cascade="all, delete-orphan",
        order_by="OrderFinancialRecord.created_at, OrderFinancialRecord.id",
    )
    notifications = db.relationship(
        "OrderNotification", back_populates="order", cascade="all, delete-orphan"
    )
    complaints = db.relationship("Complaint", back_populates="order")
    review = db.relationship("Review", back_populates="order", uselist=False, cascade="all, delete-orphan")
    customer_push_subscriptions = db.relationship(
        "CustomerPushSubscription",
        secondary=order_customer_push_subscriptions,
        back_populates="orders",
    )

    @property
    def has_weight_priced_items(self):
        return any(item.pricing_type == "weight_deposit" for item in self.items)

    @property
    def weight_priced_items(self):
        return [item for item in self.items if item.pricing_type == "weight_deposit"]

    @property
    def weights_complete(self):
        return all(item.actual_weight_kg is not None for item in self.weight_priced_items)

    @property
    def final_total(self):
        if not self.has_weight_priced_items:
            return Decimal(str(self.total or 0)).quantize(Decimal("0.01"))
        if not self.weights_complete:
            return None
        final_amount = Decimal(str(self.delivery_fee or 0))
        for item in self.items:
            final_amount += item.final_subtotal
        return final_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def final_variance(self):
        if self.final_total is None:
            return None
        return (self.final_total - Decimal(str(self.total or 0))).quantize(Decimal("0.01"))

    @property
    def settled_balance_payments(self):
        return sum(
            (Decimal(str(record.amount)) for record in self.financial_records
             if record.event_type == "balance_payment" and record.status == "settled"),
            Decimal("0.00"),
        )

    @property
    def settled_refunds(self):
        return sum(
            (Decimal(str(record.amount)) for record in self.financial_records
             if record.event_type == "refund" and record.status == "settled"),
            Decimal("0.00"),
        )

    @property
    def balance_due(self):
        variance = self.final_variance
        if variance is None or self.payment_status != "Verified" or variance <= 0:
            return None if variance is None or self.payment_status != "Verified" else Decimal("0.00")
        return max(variance - self.settled_balance_payments, Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def refund_due(self):
        variance = self.final_variance
        if variance is None or self.payment_status != "Verified" or variance >= 0:
            return None if variance is None or self.payment_status != "Verified" else Decimal("0.00")
        return max(abs(variance) - self.settled_refunds, Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def refund_deadline(self):
        return self.weighing_completed_at + timedelta(hours=48) if self.weighing_completed_at else None

    @property
    def refund_overdue(self):
        return bool(
            self.refund_due is not None
            and self.refund_due > 0
            and self.refund_deadline is not None
            and datetime.utcnow() > self.refund_deadline
        )


class OrderFinancialRecord(db.Model):
    __tablename__ = "order_financial_records"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_order_financial_records_amount_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", server_default="pending")
    payment_method = db.Column(db.String(30), nullable=False, default="bank transfer", server_default="bank transfer")
    reference = db.Column(db.String(160), nullable=False, default="", server_default="")
    notes = db.Column(db.String(500), nullable=False, default="", server_default="")
    recorded_by = db.Column(db.String(120), nullable=False, default="Owner", server_default="Owner")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.func.current_timestamp())
    settled_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order", back_populates="financial_records")


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
    actual_weight_kg = db.Column(db.Numeric(10, 3), nullable=True)
    requested_weight_kg = db.Column(db.Numeric(10, 3), nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    @property
    def final_subtotal(self):
        if self.pricing_type == "weight_deposit" and self.actual_weight_kg is not None:
            amount = Decimal(str(self.weight_price_per_kg or 0)) * Decimal(str(self.actual_weight_kg))
            return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Decimal(str(self.subtotal or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ShopUpdate(db.Model):
    __tablename__ = "shop_updates"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(160), nullable=True)
    posted_by = db.Column(db.String(80), nullable=False, default="Admin")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("order_id", name="uq_reviews_order_id"),
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(160), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending", server_default="Pending")
    owner_response = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order", back_populates="review")


class StaffPushSubscription(db.Model):
    __tablename__ = "staff_push_subscriptions"
    __table_args__ = (
        db.UniqueConstraint("staff_role", "salesperson_account_id", "endpoint_hash", name="uq_staff_push_sub_role_account_endpoint"),
    )

    id = db.Column(db.Integer, primary_key=True)
    staff_role = db.Column(db.String(32), nullable=False)
    salesperson_account_id = db.Column(db.Integer, db.ForeignKey("salesperson_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    endpoint_hash = db.Column(db.String(64), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SalespersonAccount(db.Model):
    __tablename__ = "salesperson_accounts"
    __table_args__ = (
        db.UniqueConstraint("username", name="uq_salesperson_accounts_username"),
    )

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(40), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    permissions_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    disabled_at = db.Column(db.DateTime, nullable=True)


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
