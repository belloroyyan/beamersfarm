"""Replace product pricing types with unit prices and requested kg order lines.

Revision ID: c8f41e6a2d90
Revises: b7c29d61e5a4
Create Date: 2026-10-01 15:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c8f41e6a2d90"
down_revision = "b7c29d61e5a4"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve the per-kg rate as the new single product price and make kg the
    # price unit. Inventory stock continues to represent whole sale units/birds.
    op.execute(sa.text(
        "UPDATE products "
        "SET price = COALESCE(weight_price_per_kg, price), unit = 'kg' "
        "WHERE pricing_type = 'weight_deposit'"
    ))
    # Replace only the original seed copy, never an Owner-customized description.
    op.execute(sa.text(
        "UPDATE products SET description = :description "
        "WHERE name = 'Full Chicken' AND description = :old_description"
    ).bindparams(
        description=(
            "A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. "
            "Choose the number of birds and enter one combined target weight for the whole line; "
            "the order is charged at the listed price per kilogram."
        ),
        old_description=(
            "A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. "
            "Deposit is paid before confirmation; the final price is based on its weight."
        ),
    ))

    op.add_column(
        "order_items",
        sa.Column("requested_weight_kg", sa.Numeric(10, 3), nullable=True),
    )

    # These product-level mode/rate columns are no longer used. The OrderItem
    # snapshots and Order settlement ledger remain intact for legacy orders.
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("weight_price_per_kg")
        batch_op.drop_column("pricing_type")


def downgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(
            sa.Column("pricing_type", sa.String(length=30), nullable=False, server_default="fixed")
        )
        batch_op.add_column(sa.Column("weight_price_per_kg", sa.Numeric(12, 2), nullable=True))

    # Best-effort reconstruction for products represented as per kilogram.
    op.execute(sa.text(
        "UPDATE products SET pricing_type = 'weight_deposit', "
        "weight_price_per_kg = price WHERE lower(trim(unit)) = 'kg'"
    ))
    op.drop_column("order_items", "requested_weight_kg")
