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


def _columns():
    bind = op.get_bind()
    inspector = inspect(bind)
    return {c["name"]: c for c in inspector.get_columns("shop_settings")}


def upgrade():
    columns = _columns()
    if "team_members_json" not in columns:
        # MySQL does not allow a DEFAULT on TEXT/BLOB/JSON columns.
        op.add_column(
            "shop_settings",
            sa.Column("team_members_json", sa.Text(), nullable=True),
        )

    op.execute(
        sa.text(
            "UPDATE shop_settings "
            "SET team_members_json = :default_value "
            "WHERE team_members_json IS NULL"
        ).bindparams(default_value="[]")
    )

    current = _columns().get("team_members_json")
    if current and current.get("nullable", True):
        op.alter_column(
            "shop_settings",
            "team_members_json",
            existing_type=sa.Text(),
            existing_nullable=True,
            nullable=False,
        )


def downgrade():
    columns = _columns()
    if "team_members_json" in columns:
        op.drop_column("shop_settings", "team_members_json")
