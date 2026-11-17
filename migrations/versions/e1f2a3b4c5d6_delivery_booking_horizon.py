"""Add owner-configured delivery booking horizon and requested delivery date.

Revision ID: e1f2a3b4c5d6
Revises: d6e7f8a9b0c1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "e1f2a3b4c5d6"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    settings_columns = {column["name"] for column in inspector.get_columns("shop_settings")}
    if "delivery_booking_days" not in settings_columns:
        op.add_column(
            "shop_settings",
            sa.Column("delivery_booking_days", sa.Integer(), nullable=False, server_default="7"),
        )
    order_columns = {column["name"] for column in inspect(bind).get_columns("orders")}
    if "requested_delivery_date" not in order_columns:
        op.add_column("orders", sa.Column("requested_delivery_date", sa.Date(), nullable=True))


def downgrade():
    # Intentionally retain these additive columns. The upgrade is schema-aware
    # because earlier MySQL attempts may have partially created them; dropping
    # them during downgrade could remove data that pre-dated this revision.
    pass
