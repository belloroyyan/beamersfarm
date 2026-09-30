"""Add shop updates

Revision ID: d7e3a1b5c902
Revises: c41f7a9d2b10
Create Date: 2026-09-30 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d7e3a1b5c902"
down_revision = "c41f7a9d2b10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shop_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image", sa.String(length=160), nullable=True),
        sa.Column("posted_by", sa.String(length=80), nullable=False, server_default="Admin"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("shop_updates")
