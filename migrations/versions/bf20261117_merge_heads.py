"""Merge multiple migration heads.

Revision ID: bf20261117merge
Revises: f7a9c2d4e610, bf20261117
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "bf20261117merge"
down_revision = ("f7a9c2d4e610", "bf20261117")
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"]: c for c in inspector.get_columns("shop_settings")}
    if "team_members_json" not in columns:
        op.add_column(
            "shop_settings",
            sa.Column("team_members_json", sa.Text(), nullable=True),
        )
        op.execute(
            sa.text(
                "UPDATE shop_settings SET team_members_json = :v WHERE team_members_json IS NULL"
            ).bindparams(v="[]")
        )
        op.alter_column(
            "shop_settings",
            "team_members_json",
            existing_type=sa.Text(),
            existing_nullable=True,
            nullable=False,
        )


def downgrade():
    pass
