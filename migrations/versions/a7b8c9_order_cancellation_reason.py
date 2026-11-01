"""optional cancellation reason on orders

Revision ID: a7b8c9
Revises: a2b3c4
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9"
down_revision = "a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("cancellation_reason", sa.String(length=160), nullable=True))


def downgrade():
    op.drop_column("orders", "cancellation_reason")
