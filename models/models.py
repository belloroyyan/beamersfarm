import secrets
from datetime import datetime
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", back_populates="product")

    @property
    def is_available(self):
        return self.active and self.stock > 0


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    public_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32)
    )
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), nullable=False, default="Received")
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    delivery_fee = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


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
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")
