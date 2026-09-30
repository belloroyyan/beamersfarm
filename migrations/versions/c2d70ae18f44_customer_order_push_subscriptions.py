"""Customer order-status push subscriptions

Revision ID: c2d70ae18f44
Revises: a462cf7e10ab
Create Date: 2026-09-30 16:49:00
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d70ae18f44"
down_revision = "a462cf7e10ab"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_key", sa.String(length=64), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_key", "endpoint_hash",
            name="uq_customer_push_subscriptions_customer_endpoint",
        ),
    )
    op.create_table(
        "order_customer_push_subscriptions",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["customer_push_subscriptions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("order_id", "subscription_id"),
    )


def downgrade():
    op.drop_table("order_customer_push_subscriptions")
    op.drop_table("customer_push_subscriptions")
