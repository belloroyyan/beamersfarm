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
    op.add_column(
        "salesperson_accounts",
        sa.Column("permissions_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.execute(
        sa.text("UPDATE salesperson_accounts SET permissions_json = :permissions")
        .bindparams(permissions=DEFAULT_PERMISSIONS)
    )

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
