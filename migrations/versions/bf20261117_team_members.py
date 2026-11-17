"""add team_members_json to shop_settings

Revision ID: bf20261117
Revises: zb8c9d0e1f2
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "bf20261117"
down_revision = "zb8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("shop_settings")}
    if "team_members_json" not in columns:
        op.add_column(
            "shop_settings",
            sa.Column("team_members_json", sa.Text(), nullable=False, server_default="[]"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("shop_settings")}
    if "team_members_json" in columns:
        op.drop_column("shop_settings", "team_members_json")
