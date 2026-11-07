"""Add composite indexes for common operational list and queue queries."""
from alembic import op

revision = "c9d8e7f6a5b4"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])
    op.create_index("ix_orders_batch_status", "orders", ["dispatch_batch_id", "status"])
    op.create_index("ix_orders_channel_created", "orders", ["order_channel", "created_at"])
    op.create_index("ix_order_items_order_product", "order_items", ["order_id", "product_id"])
    op.create_index("ix_community_posts_status_created", "community_posts", ["status", "created_at"])
    op.create_index("ix_community_comments_post_created", "community_comments", ["post_id", "created_at"])
    op.create_index("ix_community_notifications_customer_read_created", "community_notifications", ["customer_id", "read_at", "created_at"])
    op.create_index("ix_order_notifications_status_retry", "order_notifications", ["status", "next_attempt_at"])
    op.create_index("ix_customers_verified_active", "customers", ["email_verified", "active"])
    op.create_index("ix_analytics_created_path", "analytics_events", ["created_at", "path"])


def downgrade():
    op.drop_index("ix_analytics_created_path", table_name="analytics_events")
    op.drop_index("ix_customers_verified_active", table_name="customers")
    op.drop_index("ix_order_notifications_status_retry", table_name="order_notifications")
    op.drop_index("ix_community_notifications_customer_read_created", table_name="community_notifications")
    op.drop_index("ix_community_comments_post_created", table_name="community_comments")
    op.drop_index("ix_community_posts_status_created", table_name="community_posts")
    op.drop_index("ix_order_items_order_product", table_name="order_items")
    op.drop_index("ix_orders_channel_created", table_name="orders")
    op.drop_index("ix_orders_batch_status", table_name="orders")
    op.drop_index("ix_orders_status_created", table_name="orders")
