"""track customer last successful sign-in
Revision ID: a2b3c4d5e6f7
Revises: z1a2b3
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customers", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.create_index("ix_customers_last_login_at", "customers", ["last_login_at"])


def downgrade():
    op.drop_index("ix_customers_last_login_at", table_name="customers")
    op.drop_column("customers", "last_login_at")
