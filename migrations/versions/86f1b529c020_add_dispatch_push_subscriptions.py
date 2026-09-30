"""Add dispatch push subscriptions

Revision ID: 86f1b529c020
Revises: d7e3a1b5c902
Create Date: 2026-09-30 16:18:00
"""
from alembic import op
import sqlalchemy as sa

revision = "86f1b529c020"
down_revision = "d7e3a1b5c902"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dispatch_push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint_hash", name="uq_dispatch_push_subscriptions_endpoint_hash"),
    )


def downgrade():
    op.drop_table("dispatch_push_subscriptions")
