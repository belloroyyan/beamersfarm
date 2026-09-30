"""Role-scoped staff push subscriptions

Revision ID: a462cf7e10ab
Revises: 86f1b529c020
Create Date: 2026-09-30 16:34:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a462cf7e10ab"
down_revision = "86f1b529c020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "staff_push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_role", sa.String(length=32), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "staff_role", "endpoint_hash",
            name="uq_staff_push_subscriptions_role_endpoint_hash",
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO staff_push_subscriptions "
            "(staff_role, endpoint_hash, endpoint, p256dh, auth, created_at) "
            "SELECT 'dispatch_rider', endpoint_hash, endpoint, p256dh, auth, created_at "
            "FROM dispatch_push_subscriptions"
        )
    )
    op.drop_table("dispatch_push_subscriptions")


def downgrade():
    op.create_table(
        "dispatch_push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "endpoint_hash", name="uq_dispatch_push_subscriptions_endpoint_hash"
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO dispatch_push_subscriptions "
            "(endpoint_hash, endpoint, p256dh, auth, created_at) "
            "SELECT endpoint_hash, endpoint, p256dh, auth, created_at "
            "FROM staff_push_subscriptions WHERE staff_role = 'dispatch_rider'"
        )
    )
    op.drop_table("staff_push_subscriptions")
