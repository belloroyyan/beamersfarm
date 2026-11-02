"""customer email verification, notes, staff profiles and activity log
Revision ID: b8c9d0
Revises: a7b8c9
"""
from alembic import op
import sqlalchemy as sa
revision = "b8c9d0"
down_revision = "a7b8c9"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("customers", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("customers", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.create_table("customer_email_verifications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False), sa.Column("token", sa.String(96), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_customer_email_verifications_token", "customer_email_verifications", ["token"], unique=True)
    op.create_table("customer_notes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_by", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_customer_notes_customer_id", "customer_notes", ["customer_id"])
    op.add_column("salesperson_accounts", sa.Column("phone", sa.String(40), nullable=False, server_default=""))
    op.add_column("salesperson_accounts", sa.Column("email", sa.String(160), nullable=False, server_default=""))
    op.add_column("salesperson_accounts", sa.Column("socials", sa.Text(), nullable=False, server_default=""))
    op.add_column("salesperson_accounts", sa.Column("address", sa.Text(), nullable=False, server_default=""))
    op.add_column("salesperson_accounts", sa.Column("profile_updated_at", sa.DateTime(), nullable=True))
    op.create_table("staff_action_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("salesperson_account_id", sa.Integer(), sa.ForeignKey("salesperson_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("action", sa.String(160), nullable=False), sa.Column("detail", sa.String(500), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_staff_action_logs_salesperson_account_id", "staff_action_logs", ["salesperson_account_id"])
    op.create_index("ix_staff_action_logs_created_at", "staff_action_logs", ["created_at"])
def downgrade():
    op.drop_table("staff_action_logs")
    for col in ("profile_updated_at", "address", "socials", "email", "phone"): op.drop_column("salesperson_accounts", col)
    op.drop_table("customer_notes")
    op.drop_table("customer_email_verifications")
    op.drop_column("customers", "email_verified_at")
    op.drop_column("customers", "email_verified")
