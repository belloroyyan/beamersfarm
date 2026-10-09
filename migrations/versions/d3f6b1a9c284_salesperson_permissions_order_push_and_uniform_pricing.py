"""Add configurable Salesperson permissions and uniform Full Chicken pricing.

Revision ID: d3f6b1a9c284
Revises: a91d2e4f6b80
Create Date: 2026-10-02 19:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d3f6b1a9c284"
down_revision = "a91d2e4f6b80"
branch_labels = None
depends_on = None

DEFAULT_PERMISSIONS = (
    '{"change_order_status":true,"print_customer_receipts":true,'
    '"receive_order_alerts":true,"record_weigh_ins":true,'
    '"verify_payments":true,"view_complaints":false,'
    '"view_customer_details":true,"view_inventory":false}'
)


def upgrade():
    bind = op.get_bind()
    account_columns = {column["name"]: column for column in sa.inspect(bind).get_columns("salesperson_accounts")}
    if "permissions_json" not in account_columns:
        # MySQL does not allow a default value on TEXT columns. Add it
        # nullable, backfill existing rows, then enforce NOT NULL below.
        op.add_column(
            "salesperson_accounts",
            sa.Column("permissions_json", sa.Text(), nullable=True),
        )
    op.execute(
        sa.text(
            "UPDATE salesperson_accounts SET permissions_json = :permissions "
            "WHERE permissions_json IS NULL OR permissions_json = ''"
        )
        .bindparams(permissions=DEFAULT_PERMISSIONS)
    )
    if account_columns.get("permissions_json", {}).get("nullable", True) and bind.dialect.name == "sqlite":
        # SQLite has no ALTER COLUMN support, so let Alembic recreate the
        # small account table after the backfill.
        with op.batch_alter_table("salesperson_accounts", recreate="always") as batch:
            batch.alter_column("permissions_json", existing_type=sa.Text(), nullable=False)
    elif account_columns.get("permissions_json", {}).get("nullable", True):
        # MySQL can change TEXT nullability directly, but must not receive a
        # TEXT default value.
        op.alter_column("salesperson_accounts", "permissions_json", existing_type=sa.Text(), nullable=False)

    with op.batch_alter_table("staff_push_subscriptions", recreate="always") as batch:
        batch.drop_constraint("uq_staff_push_subscriptions_role_endpoint_hash", type_="unique")
        batch.add_column(sa.Column("salesperson_account_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_staff_push_salesperson_account",
            "salesperson_accounts",
            ["salesperson_account_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_staff_push_subscriptions_salesperson_account_id", ["salesperson_account_id"])
        batch.create_unique_constraint(
            "uq_staff_push_sub_account_endpoint",
            ["staff_role", "salesperson_account_id", "endpoint_hash"],
        )

    # The next migration sets the ordinary Full Chicken price unit to kg and
    # captures the customer's combined requested kg; no deposit workflow is used.
    op.execute(
        sa.text(
            "UPDATE products SET unit = 'bird' WHERE lower(name) = 'full chicken'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE products SET description = replace(description, "
            "'Choose the number of birds and enter one combined target weight for the whole line; "
            "the order is charged at the listed price per kilogram.', "
            "'Sold per bird at the listed price.') "
            "WHERE lower(name) = 'full chicken' AND lower(description) LIKE '%combined target weight%'"
        )
    )


def downgrade():
    # Restore the historical per-kg catalog unit if rolling back this release.
    op.execute(sa.text("UPDATE products SET unit = 'kg' WHERE lower(name) = 'full chicken' AND lower(unit) = 'bird'"))
    with op.batch_alter_table("staff_push_subscriptions", recreate="always") as batch:
        batch.drop_constraint("uq_staff_push_sub_account_endpoint", type_="unique")
        batch.drop_index("ix_staff_push_subscriptions_salesperson_account_id")
        batch.drop_constraint("fk_staff_push_salesperson_account", type_="foreignkey")
        batch.drop_column("salesperson_account_id")
        batch.create_unique_constraint(
            "uq_staff_push_subscriptions_role_endpoint_hash",
            ["staff_role", "endpoint_hash"],
        )
    op.drop_column("salesperson_accounts", "permissions_json")
