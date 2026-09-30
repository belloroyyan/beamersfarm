"""Add featured flag for homepage quick menu

Revision ID: c41f7a9d2b10
Revises: b1313159527d
Create Date: 2026-09-30 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c41f7a9d2b10"
down_revision = "b1313159527d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(
            sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("featured")
