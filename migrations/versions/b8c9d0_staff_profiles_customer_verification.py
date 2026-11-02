"""customer email verification, notes, staff profiles and activity log

Revision ID: b8c9d0
Revises: a7b8c9

This migration is deliberately idempotent because MySQL DDL is not
transactional. A previous deployment may have created some objects before
failing, so each column, table and index is checked before creation.
"""
from alembic import op
import sqlalchemy as sa

revision = "b8c9d0"
down_revision = "a7b8c9"
branch_labels = None
depends_on = None


def _inspector():
    # Recreate after each DDL operation so MySQL schema changes are visible.
    return sa.inspect(op.get_bind())


def _add_column_if_missing(table_name, column):
    inspector = _inspector()
    if table_name in inspector.get_table_names():
        existing = {item["name"] for item in inspector.get_columns(table_name)}
        if column.name not in existing:
            op.add_column(table_name, column)


def _create_table_if_missing(name, *columns, **kwargs):
    if name not in _inspector().get_table_names():
        op.create_table(name, *columns, **kwargs)


def _create_index_if_missing(name, table_name, columns, unique=False):
    inspector = _inspector()
    if table_name in inspector.get_table_names():
        existing = {item["name"] for item in inspector.get_indexes(table_name)}
        # Unique constraints may be reported separately from ordinary indexes.
        existing_constraints = {item["name"] for item in inspector.get_unique_constraints(table_name)}
        if name not in existing and name not in existing_constraints:
            op.create_index(name, table_name, columns, unique=unique)


def upgrade():
    _add_column_if_missing(
        "customers",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_if_missing(
        "customers",
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
    )

    _create_table_if_missing(
        "customer_email_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(96), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    _create_index_if_missing(
        "ix_customer_email_verifications_token",
        "customer_email_verifications",
        ["token"],
        unique=True,
    )

    _create_table_if_missing(
        "customer_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _create_index_if_missing("ix_customer_notes_customer_id", "customer_notes", ["customer_id"])

    for column in (
        sa.Column("phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("email", sa.String(160), nullable=False, server_default=""),
        sa.Column("socials", sa.Text(), nullable=False, server_default=""),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("profile_updated_at", sa.DateTime(), nullable=True),
    ):
        _add_column_if_missing("salesperson_accounts", column)

    _create_table_if_missing(
        "staff_action_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("salesperson_account_id", sa.Integer(), sa.ForeignKey("salesperson_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(160), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _create_index_if_missing(
        "ix_staff_action_logs_salesperson_account_id",
        "staff_action_logs",
        ["salesperson_account_id"],
    )
    _create_index_if_missing("ix_staff_action_logs_created_at", "staff_action_logs", ["created_at"])


def downgrade():
    # Keep downgrade behavior explicit; this revision may have adopted objects
    # that pre-dated it, so operators should not run downgrade blindly.
    op.drop_table("staff_action_logs")
    for col in ("profile_updated_at", "address", "socials", "email", "phone"):
        op.drop_column("salesperson_accounts", col)
    op.drop_table("customer_notes")
    op.drop_table("customer_email_verifications")
    op.drop_column("customers", "email_verified_at")
    op.drop_column("customers", "email_verified")
