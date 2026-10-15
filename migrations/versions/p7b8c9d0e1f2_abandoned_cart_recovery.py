"""Persist signed-in carts for one-time recovery notifications."""
from alembic import op
import sqlalchemy as sa
revision = "p7b8c9d0e1f2"
down_revision = "n6a7b8c9d0e1"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table(
        "abandoned_carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("cart_json", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("recovery_sent_at", sa.DateTime(), nullable=True),
        sa.Column("recovered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", name="uq_abandoned_carts_customer"),
    )
    op.create_index("ix_abandoned_carts_customer_id", "abandoned_carts", ["customer_id"])
    op.create_index("ix_abandoned_carts_last_activity_at", "abandoned_carts", ["last_activity_at"])
def downgrade():
    op.drop_index("ix_abandoned_carts_last_activity_at", table_name="abandoned_carts")
    op.drop_index("ix_abandoned_carts_customer_id", table_name="abandoned_carts")
    op.drop_table("abandoned_carts")
