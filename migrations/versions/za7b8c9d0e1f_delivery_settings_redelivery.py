"""Configurable delivery settings, preferred windows, and redelivery requests."""
from alembic import op
import sqlalchemy as sa
revision = "za7b8c9d0e1f"
down_revision = ("c5d6e7f809a0", "z1a2b3")
branch_labels = None
depends_on = None
def upgrade():
    with op.batch_alter_table("shop_settings") as batch:
        batch.add_column(sa.Column("delivery_open_time", sa.String(5), nullable=False, server_default="07:00"))
        batch.add_column(sa.Column("delivery_close_time", sa.String(5), nullable=False, server_default="19:00"))
        batch.add_column(sa.Column("auto_shop_hours", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("delivery_windows_json", sa.Text(), nullable=False, server_default='["9:00 AM – 11:00 AM", "3:00 PM – 5:00 PM"]'))
        batch.add_column(sa.Column("closure_channels_json", sa.String(120), nullable=False, server_default='["push", "whatsapp", "email"]'))
    with op.batch_alter_table("dispatch_batches") as batch:
        batch.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("preferred_delivery_window", sa.String(120), nullable=True))
    op.create_table("delivery_redelivery_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_type", sa.String(20), nullable=False, server_default="redelivery"),
        sa.Column("preferred_window", sa.String(120), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_delivery_redelivery_requests_order_id", "delivery_redelivery_requests", ["order_id"])
    op.create_index("ix_delivery_redelivery_requests_customer_id", "delivery_redelivery_requests", ["customer_id"])
    op.create_index("ix_delivery_redelivery_requests_status", "delivery_redelivery_requests", ["status"])
def downgrade():
    op.drop_index("ix_delivery_redelivery_requests_status", table_name="delivery_redelivery_requests")
    op.drop_index("ix_delivery_redelivery_requests_customer_id", table_name="delivery_redelivery_requests")
    op.drop_index("ix_delivery_redelivery_requests_order_id", table_name="delivery_redelivery_requests")
    op.drop_table("delivery_redelivery_requests")
    with op.batch_alter_table("orders") as batch: batch.drop_column("preferred_delivery_window")
    with op.batch_alter_table("dispatch_batches") as batch: batch.drop_column("closed_at")
    with op.batch_alter_table("shop_settings") as batch:
        for name in ("closure_channels_json", "delivery_windows_json", "auto_shop_hours", "delivery_close_time", "delivery_open_time"): batch.drop_column(name)
