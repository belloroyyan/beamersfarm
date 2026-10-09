"""Add dual payment metadata for Paystack and Opay transfer.

Revision ID: g7b8c9d0e1f2
Revises: f6a8c2d4e901
"""
from alembic import op
import sqlalchemy as sa

revision = "g7b8c9d0e1f2"
down_revision = "f6a8c2d4e901"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("email", sa.String(length=160), nullable=True))
    op.add_column("orders", sa.Column("payment_method", sa.String(length=30), nullable=True))
    op.add_column("orders", sa.Column("payment_provider", sa.String(length=30), nullable=True))
    op.add_column("orders", sa.Column("payment_reference", sa.String(length=160), nullable=True))
    op.add_column("orders", sa.Column("payment_channel", sa.String(length=30), nullable=True))
    op.add_column("orders", sa.Column("payment_initiated_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("payment_failure_reason", sa.String(length=500), nullable=True))
    op.execute(sa.text("UPDATE orders SET payment_method = 'bank_transfer' WHERE payment_method IS NULL"))
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("orders", recreate="always") as batch:
            batch.alter_column("payment_method", existing_type=sa.String(length=30), nullable=False, server_default="bank_transfer")
    else:
        op.alter_column(
            "orders", "payment_method", existing_type=sa.String(length=30), nullable=False,
            server_default="bank_transfer",
        )
    op.create_index("ix_orders_payment_reference", "orders", ["payment_reference"], unique=False)


def downgrade():
    op.drop_index("ix_orders_payment_reference", table_name="orders")
    op.drop_column("orders", "payment_failure_reason")
    op.drop_column("orders", "payment_initiated_at")
    op.drop_column("orders", "payment_channel")
    op.drop_column("orders", "payment_reference")
    op.drop_column("orders", "payment_provider")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "email")
