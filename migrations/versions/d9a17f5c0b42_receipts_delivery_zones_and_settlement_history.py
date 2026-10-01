"""Printable receipts, configurable delivery zones, pickup, and settlements

Revision ID: d9a17f5c0b42
Revises: b67a3f2d9c18
Create Date: 2026-10-01 10:45:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "d9a17f5c0b42"
down_revision = "b67a3f2d9c18"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("is_pickup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("fee >= 0", name="ck_delivery_zones_fee_nonnegative"),
        sa.UniqueConstraint("name", name="uq_delivery_zones_name"),
    )

    op.add_column(
        "orders",
        sa.Column("fulfillment_type", sa.String(length=20), nullable=False, server_default="delivery"),
    )
    op.add_column(
        "orders",
        sa.Column("delivery_zone_name", sa.String(length=100), nullable=False, server_default="Pre-zone delivery"),
    )
    op.add_column("orders", sa.Column("weighing_completed_at", sa.DateTime(), nullable=True))
    op.add_column("order_items", sa.Column("actual_weight_kg", sa.Numeric(10, 3), nullable=True))

    op.create_table(
        "order_financial_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(length=30), nullable=False, server_default="bank transfer"),
        sa.Column("reference", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("notes", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.String(length=120), nullable=False, server_default="Owner"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_order_financial_records_amount_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_order_financial_records_order_id", "order_financial_records", ["order_id"])

    now = datetime.utcnow()
    zones = sa.table(
        "delivery_zones",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("fee", sa.Numeric(12, 2)),
        sa.column("is_pickup", sa.Boolean),
        sa.column("active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        zones,
        [
            {
                "name": "Osogbo — Standard delivery",
                "description": "Standard Osogbo delivery tier. Please confirm with us if you are unsure whether your neighborhood is included.",
                "fee": 1500.00,
                "is_pickup": False,
                "active": True,
                "sort_order": 10,
                "created_at": now,
            },
            {
                "name": "Farm pickup (Elapop Estate)",
                "description": "Collect your order from Beamers Farm; no delivery fee.",
                "fee": 0.00,
                "is_pickup": True,
                "active": True,
                "sort_order": 0,
                "created_at": now,
            },
        ],
    )

    op.execute(
        sa.text(
            "INSERT INTO order_financial_records "
            "(order_id, event_type, amount, status, payment_method, reference, notes, recorded_by, created_at, settled_at) "
            "SELECT id, 'initial_payment', total, "
            "CASE WHEN payment_status = 'Verified' THEN 'settled' ELSE 'pending' END, "
            "'bank transfer', '', 'Pay-now amount carried forward during the receipt-history upgrade', "
            "'Owner', created_at, CASE WHEN payment_status = 'Verified' THEN COALESCE(payment_verified_at, created_at) ELSE NULL END "
            "FROM orders WHERE total > 0"
        )
    )


def downgrade():
    op.drop_index("ix_order_financial_records_order_id", table_name="order_financial_records")
    op.drop_table("order_financial_records")
    op.drop_column("order_items", "actual_weight_kg")
    op.drop_column("orders", "weighing_completed_at")
    op.drop_column("orders", "delivery_zone_name")
    op.drop_column("orders", "fulfillment_type")
    op.drop_table("delivery_zones")
