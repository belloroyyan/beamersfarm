"""Store staff attribution for order weight entries.

Revision ID: b7c29d61e5a4
Revises: e3f19a4c7d62
Create Date: 2026-10-01 12:06:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "b7c29d61e5a4"
down_revision = "e3f19a4c7d62"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("weighing_recorded_by", sa.String(length=120), nullable=True))


def downgrade():
    op.drop_column("orders", "weighing_recorded_by")
