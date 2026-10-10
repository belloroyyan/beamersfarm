"""Add first-party analytics and automatic review publication setting."""
from alembic import op
import sqlalchemy as sa
revision="m5f6a7b8c9d0"
down_revision="l4e5f6a7b8c9"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("shop_settings", sa.Column("reviews_auto_publish", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("analytics_events", sa.Column("id", sa.Integer(), nullable=False), sa.Column("event_type", sa.String(40), nullable=False, server_default="page_view"), sa.Column("path", sa.String(255), nullable=False), sa.Column("referrer", sa.String(500), nullable=False, server_default=""), sa.Column("user_agent", sa.String(500), nullable=False, server_default=""), sa.Column("customer_id", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["customer_id"],["customers.id"],ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_analytics_events_customer_id", "analytics_events", ["customer_id"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
def downgrade():
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events"); op.drop_index("ix_analytics_events_customer_id", table_name="analytics_events"); op.drop_table("analytics_events"); op.drop_column("shop_settings", "reviews_auto_publish")
