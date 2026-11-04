"""Add OPay checkout, coupon gifting, wishlists, verification codes and campaigns."""

from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "z1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("payment_checkout_url", sa.String(length=1000), nullable=True))
    op.add_column("coupons", sa.Column("auto_gift_new_customers", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("coupons", sa.Column("gift_template_id", sa.Integer(), nullable=True))
    op.create_index("ix_coupons_gift_template_id", "coupons", ["gift_template_id"])

    op.create_table(
        "customer_email_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("requests_in_window", sa.Integer(), server_default="1", nullable=False),
        sa.Column("request_window_started_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("customer_id", name="uq_customer_email_codes_customer"),
    )
    op.create_index("ix_customer_email_codes_customer_id", "customer_email_codes", ["customer_id"])

    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("customer_id", "product_id", name="uq_wishlist_customer_product"),
    )
    op.create_index("ix_wishlist_items_customer_id", "wishlist_items", ["customer_id"])
    op.create_index("ix_wishlist_items_product_id", "wishlist_items", ["product_id"])

    op.create_table(
        "customer_message_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("channels_json", sa.String(length=200), nullable=False, server_default="[]"),
        sa.Column("attachment_names", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=120), nullable=False, server_default="Owner"),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_customer_message_campaigns_created_at", "customer_message_campaigns", ["created_at"])

    op.create_table(
        "customer_message_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("customer_message_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("provider_message_id", sa.String(length=180), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("campaign_id", "customer_id", "channel", name="uq_customer_message_delivery_campaign_customer_channel"),
    )
    op.create_index("ix_customer_message_deliveries_campaign_id", "customer_message_deliveries", ["campaign_id"])
    op.create_index("ix_customer_message_deliveries_customer_id", "customer_message_deliveries", ["customer_id"])


def downgrade():
    op.drop_index("ix_customer_message_deliveries_customer_id", table_name="customer_message_deliveries")
    op.drop_index("ix_customer_message_deliveries_campaign_id", table_name="customer_message_deliveries")
    op.drop_table("customer_message_deliveries")
    op.drop_index("ix_customer_message_campaigns_created_at", table_name="customer_message_campaigns")
    op.drop_table("customer_message_campaigns")
    op.drop_index("ix_wishlist_items_product_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_customer_id", table_name="wishlist_items")
    op.drop_table("wishlist_items")
    op.drop_index("ix_customer_email_codes_customer_id", table_name="customer_email_codes")
    op.drop_table("customer_email_codes")
    op.drop_index("ix_coupons_gift_template_id", table_name="coupons")
    op.drop_column("coupons", "gift_template_id")
    op.drop_column("coupons", "auto_gift_new_customers")
    op.drop_column("orders", "payment_checkout_url")
