"""add package discount percentages

Revision ID: x9y0z1
Revises: w4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa

revision = "x9y0z1"
down_revision = "w4e5f6a7b8c9"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("product_packages", sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"))

def downgrade():
    op.drop_column("product_packages", "discount_percent")
