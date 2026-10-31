"""allow several processing methods per order line

Revision ID: a2b3c4
Revises: z1a2b3
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4"
down_revision = "z1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    # Up to 8 options of 120 characters, joined with ", ".
    with op.batch_alter_table("order_items") as batch:
        batch.alter_column("processing_method", existing_type=sa.String(120), type_=sa.String(1000),
                           existing_nullable=False, existing_server_default="")


def downgrade():
    with op.batch_alter_table("order_items") as batch:
        batch.alter_column("processing_method", existing_type=sa.String(1000), type_=sa.String(120),
                           existing_nullable=False, existing_server_default="")
