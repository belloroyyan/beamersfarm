"""processing options, dispatch batches, persistent vaults, and notice links
Revision ID: z1a2b3
Revises: y0z1a2
"""
from alembic import op
import sqlalchemy as sa
revision="z1a2b3"
down_revision="y0z1a2"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("products",sa.Column("processing_options",sa.Text(),nullable=False,server_default=""))
    op.add_column("order_items",sa.Column("processing_method",sa.String(120),nullable=False,server_default=""))
    op.add_column("drop_shares",sa.Column("access_token",sa.String(80),nullable=True))
    op.add_column("drop_shares",sa.Column("one_time",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("customer_notices",sa.Column("related_url",sa.String(500),nullable=True))
    op.add_column("orders",sa.Column("dispatch_batch_id",sa.Integer(),nullable=True))
    op.create_table("dispatch_batches",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("window_start",sa.DateTime(),nullable=False),sa.Column("window_end",sa.DateTime(),nullable=False),sa.Column("weight_limit",sa.Numeric(12,3),nullable=False,server_default="50"),sa.Column("assigned_weight",sa.Numeric(12,3),nullable=False,server_default="0"),sa.Column("status",sa.String(24),nullable=False,server_default="open"))
    op.create_foreign_key("fk_orders_dispatch_batch","orders","dispatch_batches",["dispatch_batch_id"],["id"],ondelete="SET NULL")
    op.add_column("shop_settings",sa.Column("dispatch_batch_hours",sa.Numeric(5,2),nullable=False,server_default="2"))
    op.add_column("shop_settings",sa.Column("dispatch_batch_weight_limit",sa.Numeric(12,3),nullable=False,server_default="50"))
def downgrade():
    op.drop_column("shop_settings","dispatch_batch_weight_limit"); op.drop_column("shop_settings","dispatch_batch_hours"); op.drop_constraint("fk_orders_dispatch_batch","orders",type_="foreignkey"); op.drop_column("orders","dispatch_batch_id"); op.drop_table("dispatch_batches"); op.drop_column("customer_notices","related_url"); op.drop_column("drop_shares","one_time"); op.drop_column("drop_shares","access_token"); op.drop_column("order_items","processing_method"); op.drop_column("products","processing_options")
