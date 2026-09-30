"""Add public UUID order identifiers

Revision ID: b1313159527d
Revises: 9f9887367545
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "b1313159527d"
down_revision = "9f9887367545"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("public_id", sa.String(length=36), nullable=True))
    connection = op.get_bind()
    order_ids = [row[0] for row in connection.execute(sa.text("SELECT id FROM orders"))]
    for order_id in order_ids:
        connection.execute(
            sa.text("UPDATE orders SET public_id = :public_id WHERE id = :id"),
            {"public_id": str(uuid.uuid4()), "id": order_id},
        )
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("public_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_unique_constraint("uq_orders_public_id", ["public_id"])


def downgrade():
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_constraint("uq_orders_public_id", type_="unique")
        batch_op.drop_column("public_id")
