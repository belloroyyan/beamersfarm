"""Add owner-managed product recommendations.

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa

revision = "h8c9d0e1f2a3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("products", "recommended")
