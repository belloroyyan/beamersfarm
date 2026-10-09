"""Add verified customer reviews.

Revision ID: j9d0e1f2a3b4
Revises: h8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa

revision = "j9d0e1f2a3b4"
down_revision = "h8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pending"),
        sa.Column("owner_response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        sa.UniqueConstraint("order_id", name="uq_reviews_order_id"),
    )
    op.create_index("ix_reviews_order_id", "reviews", ["order_id"], unique=False)


def downgrade():
    op.drop_index("ix_reviews_order_id", table_name="reviews")
    op.drop_table("reviews")
