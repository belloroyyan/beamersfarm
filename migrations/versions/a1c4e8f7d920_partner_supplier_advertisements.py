"""Add independent partner advertisements and supplier contact details.

Revision ID: a1c4e8f7d920
Revises: j9d0e1f2a3b4
"""

from alembic import op
import sqlalchemy as sa

revision = "a1c4e8f7d920"
down_revision = "j9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partner_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="Other"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("price_note", sa.String(length=180), nullable=False, server_default="Contact supplier for current price"),
        sa.Column("supplier_name", sa.String(length=120), nullable=False),
        sa.Column("supplier_phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("supplier_email", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("supplier_website", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("supplier_location", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("social_links_json", sa.Text(), nullable=False),
        sa.Column("image", sa.String(length=160), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_partner_listings_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partner_listings_active_sort", "partner_listings", ["active", "sort_order"])


def downgrade():
    op.drop_index("ix_partner_listings_active_sort", table_name="partner_listings")
    op.drop_table("partner_listings")
