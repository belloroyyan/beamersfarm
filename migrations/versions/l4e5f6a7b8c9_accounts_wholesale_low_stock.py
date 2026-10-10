"""Add wholesale requests and configurable low-stock alerts."""
from alembic import op
import sqlalchemy as sa
revision = "l4e5f6a7b8c9"
down_revision = ("j9d0e1f2a3b4", "k3d4e5f6a7b8")
branch_labels = None
depends_on = None
def upgrade():
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    cols = {c["name"] for c in insp.get_columns("products")}
    if "low_stock_threshold" not in cols:
        op.add_column("products", sa.Column("low_stock_threshold", sa.Numeric(12, 3), nullable=False, server_default="5.000"))
    if "wholesale_orders" not in tables:
      op.create_table("wholesale_orders",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True), sa.Column("customer_name", sa.String(120), nullable=False),
        sa.Column("business_name", sa.String(160), nullable=False), sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("email", sa.String(160), nullable=True), sa.Column("delivery_address", sa.Text(), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=True), sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="New"), sa.Column("owner_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_id"))
      op.create_index("ix_wholesale_orders_customer_id", "wholesale_orders", ["customer_id"])
    if "wholesale_order_items" not in tables:
      op.create_table("wholesale_order_items",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("wholesale_order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True), sa.Column("product_name", sa.String(120), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("unit", sa.String(80), nullable=False, server_default="per pack"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["wholesale_order_id"], ["wholesale_orders.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
def downgrade():
    op.drop_table("wholesale_order_items"); op.drop_index("ix_wholesale_orders_customer_id", table_name="wholesale_orders"); op.drop_table("wholesale_orders"); op.drop_column("products", "low_stock_threshold")
