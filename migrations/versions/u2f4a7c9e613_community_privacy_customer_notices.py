"""Add privacy controls, community posting blocks, and customer notices.

Revision ID: u2f4a7c9e613
Revises: s0a1b2c3d4e5, t1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "u2f4a7c9e613"
down_revision = ("s0a1b2c3d4e5", "t1c2d3e4f5a6")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers") as batch:
        batch.add_column(sa.Column("community_profile_public", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("community_posting_blocked", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("community_posts") as batch:
        batch.add_column(sa.Column("considering", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "customer_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("message", sa.String(700), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="account"),
        sa.Column("created_by", sa.String(120), nullable=False, server_default="Beamers Farm"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_customer_notices_customer_id", "customer_notices", ["customer_id"])
    op.create_index("ix_customer_notices_created_at", "customer_notices", ["created_at"])


def downgrade():
    op.drop_index("ix_customer_notices_created_at", table_name="customer_notices")
    op.drop_index("ix_customer_notices_customer_id", table_name="customer_notices")
    op.drop_table("customer_notices")
    with op.batch_alter_table("community_posts") as batch:
        batch.drop_column("considering")
    with op.batch_alter_table("customers") as batch:
        batch.drop_column("community_posting_blocked")
        batch.drop_column("community_profile_public")
