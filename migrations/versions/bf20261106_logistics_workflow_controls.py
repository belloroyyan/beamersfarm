"""Add customer cancellation request tracking."""
from alembic import op
import sqlalchemy as sa

revision = "bf20261106"
down_revision = "za7b8c9d0e1f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("cancellation_requested_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("cancellation_request_reason", sa.String(length=500), nullable=False, server_default=""))
    op.execute("UPDATE orders SET status = 'Prepared' WHERE status = 'Preparing'")


def downgrade():
    op.execute("UPDATE orders SET status = 'Preparing' WHERE status = 'Prepared'")
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("cancellation_request_reason")
        batch.drop_column("cancellation_requested_at")
