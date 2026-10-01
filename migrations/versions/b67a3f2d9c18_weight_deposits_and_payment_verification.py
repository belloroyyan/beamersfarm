"""Add weight-deposit pricing and payment verification

Revision ID: b67a3f2d9c18
Revises: c2d70ae18f44
Create Date: 2026-10-01 06:45:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b67a3f2d9c18"
down_revision = "c2d70ae18f44"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("pricing_type", sa.String(length=30), nullable=False, server_default="fixed"),
    )
    op.add_column("products", sa.Column("weight_price_per_kg", sa.Numeric(12, 2), nullable=True))

    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(length=30), nullable=False, server_default="Unverified"),
    )
    op.add_column("orders", sa.Column("payment_verified_at", sa.DateTime(), nullable=True))

    op.add_column(
        "order_items",
        sa.Column("unit", sa.String(length=80), nullable=False, server_default="per pack"),
    )
    op.add_column(
        "order_items",
        sa.Column("pricing_type", sa.String(length=30), nullable=False, server_default="fixed"),
    )
    op.add_column("order_items", sa.Column("weight_price_per_kg", sa.Numeric(12, 2), nullable=True))

    # Apply the owner-approved example to the existing seeded catalog item.
    op.execute(
        sa.text(
            "UPDATE products SET price = 4500.00, pricing_type = 'weight_deposit', "
            "weight_price_per_kg = 4500.00 WHERE name = 'Full Chicken'"
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "UPDATE products SET price = 8500.00, pricing_type = 'fixed', "
            "weight_price_per_kg = NULL WHERE name = 'Full Chicken' "
            "AND price = 4500.00 AND weight_price_per_kg = 4500.00"
        )
    )
    op.drop_column("order_items", "weight_price_per_kg")
    op.drop_column("order_items", "pricing_type")
    op.drop_column("order_items", "unit")
    op.drop_column("orders", "payment_verified_at")
    op.drop_column("orders", "payment_status")
    op.drop_column("products", "weight_price_per_kg")
    op.drop_column("products", "pricing_type")
