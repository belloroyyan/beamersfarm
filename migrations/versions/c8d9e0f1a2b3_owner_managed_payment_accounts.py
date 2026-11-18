"""Add owner-managed bank accounts."""
from alembic import op
import sqlalchemy as sa
revision = "c8d9e0f1a2b3"
down_revision = "zb8c9d0e1f2"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("payment_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("bank_name", sa.String(100), nullable=False), sa.Column("account_number", sa.String(30), nullable=False), sa.Column("account_name", sa.String(120), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.execute("INSERT INTO payment_accounts (bank_name, account_number, account_name, active, sort_order, created_at) VALUES ('LOTUS Bank', '1015222964', 'Beamers Farms', 1, 0, CURRENT_TIMESTAMP)")
def downgrade():
    op.drop_table("payment_accounts")
