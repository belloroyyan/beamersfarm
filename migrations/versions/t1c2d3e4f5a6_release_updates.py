"""Add community controls, customer coupon gifts, and partner form invites."""
from alembic import op
import sqlalchemy as sa
revision = "t1c2d3e4f5a6"
down_revision = "n6a7b8c9d0e1"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("shop_settings", sa.Column("community_open", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("shop_settings", sa.Column("community_closed_message", sa.String(500), nullable=False, server_default="The community is currently closed."))
    with op.batch_alter_table("coupons") as batch:
        batch.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_coupons_customer_id_customers", "customers", ["customer_id"], ["id"], ondelete="SET NULL")
        batch.add_column(sa.Column("gift_message", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("gifted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_coupons_customer_id", "coupons", ["customer_id"])
    op.add_column("partner_listings", sa.Column("submitted_via_invite", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("partner_ad_invites", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(), nullable=False), sa.Column("used_at", sa.DateTime(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("created_by", sa.String(120), nullable=False, server_default="Owner"))
    op.create_index("ix_partner_ad_invites_token_hash", "partner_ad_invites", ["token_hash"])
    op.create_index("ix_partner_ad_invites_expires_at", "partner_ad_invites", ["expires_at"])
def downgrade():
    op.drop_index("ix_partner_ad_invites_expires_at", table_name="partner_ad_invites")
    op.drop_index("ix_partner_ad_invites_token_hash", table_name="partner_ad_invites")
    op.drop_table("partner_ad_invites")
    op.drop_column("partner_listings", "submitted_via_invite")
    op.drop_index("ix_coupons_customer_id", table_name="coupons")
    with op.batch_alter_table("coupons") as batch:
        batch.drop_column("gifted_at")
        batch.drop_column("gift_message")
        batch.drop_column("customer_id")
    op.drop_column("shop_settings", "community_closed_message")
    op.drop_column("shop_settings", "community_open")
