"""Record role and staff name for initial payment verification.

Revision ID: a91d2e4f6b80
Revises: c8f41e6a2d90
Create Date: 2026-10-02 18:53:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a91d2e4f6b80"
down_revision = "c8f41e6a2d90"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("payment_verified_by_role", sa.String(length=20), nullable=True))
    op.add_column("orders", sa.Column("payment_verified_by_name", sa.String(length=120), nullable=True))


def downgrade():
    op.drop_column("orders", "payment_verified_by_name")
    op.drop_column("orders", "payment_verified_by_role")
