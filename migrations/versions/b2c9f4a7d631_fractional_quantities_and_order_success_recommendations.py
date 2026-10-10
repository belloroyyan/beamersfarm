"""Support fractional catalog quantities and partner recommendations.

Revision ID: b2c9f4a7d631
Revises: a1c4e8f7d920
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c9f4a7d631"
down_revision = "a1c4e8f7d920"
branch_labels = None
depends_on = None


QUANTITY_TYPE = sa.Numeric(12, 3)


def _alter_quantity(table_name, column_name, new_type, old_type):
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=old_type,
                type_=new_type,
                existing_nullable=False,
            )
    else:
        op.alter_column(
            table_name,
            column_name,
            existing_type=old_type,
            type_=new_type,
            existing_nullable=False,
        )


def upgrade():
    op.add_column(
        "products",
        sa.Column("allow_fractional_quantity", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "partner_listings",
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _alter_quantity("products", "stock", QUANTITY_TYPE, sa.Integer())
    _alter_quantity("order_items", "quantity", QUANTITY_TYPE, sa.Integer())


def downgrade():
    bind = op.get_bind()
    fractional_stock = bind.execute(sa.text(
        "SELECT id FROM products WHERE stock != CAST(stock AS INTEGER) LIMIT 1"
    )).first()
    fractional_orders = bind.execute(sa.text(
        "SELECT id FROM order_items WHERE quantity != CAST(quantity AS INTEGER) LIMIT 1"
    )).first()
    if fractional_stock or fractional_orders:
        raise RuntimeError("Cannot downgrade while fractional quantities exist; restore whole-unit values first.")
    _alter_quantity("order_items", "quantity", sa.Integer(), QUANTITY_TYPE)
    _alter_quantity("products", "stock", sa.Integer(), QUANTITY_TYPE)
    op.drop_column("partner_listings", "recommended")
    op.drop_column("products", "allow_fractional_quantity")
