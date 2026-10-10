"""Add optional customer accounts and link orders.

Revision ID: k3d4e5f6a7b8
Revises: b2c9f4a7d631
"""
from alembic import op
import sqlalchemy as sa

revision = "k3d4e5f6a7b8"
down_revision = "b2c9f4a7d631"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("push_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("whatsapp_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uq_customers_phone"),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("orders") as batch_op:
            batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_orders_customer_id", "customers", ["customer_id"], ["id"], ondelete="SET NULL")
            batch_op.create_index("ix_orders_customer_id", ["customer_id"])
    else:
        op.add_column("orders", sa.Column("customer_id", sa.Integer(), nullable=True))
        op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
        op.create_foreign_key("fk_orders_customer_id", "orders", "customers", ["customer_id"], ["id"], ondelete="SET NULL")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("orders") as batch_op:
            batch_op.drop_index("ix_orders_customer_id")
            batch_op.drop_constraint("fk_orders_customer_id", type_="foreignkey")
            batch_op.drop_column("customer_id")
    else:
        op.drop_constraint("fk_orders_customer_id", "orders", type_="foreignkey")
        op.drop_index("ix_orders_customer_id", table_name="orders")
        op.drop_column("orders", "customer_id")
    op.drop_table("customers")
