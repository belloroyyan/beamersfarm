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


def _state():
    insp = sa.inspect(op.get_bind())
    return insp


def upgrade():
    # MySQL commits each ALTER TABLE immediately, so a previous failed deploy
    # can leave this migration half-applied. Every step checks first so the
    # migration can safely be re-run.
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    insp = _state()
    sp_cols = {c["name"] for c in insp.get_columns("salesperson_accounts")}
    if "permissions_json" not in sp_cols:
        # MySQL does not allow a default value on TEXT columns. Add it
        # nullable, backfill existing rows, then enforce NOT NULL below.
        op.add_column("salesperson_accounts", sa.Column("permissions_json", sa.Text(), nullable=True))
    op.execute(
        sa.text("UPDATE salesperson_accounts SET permissions_json = :permissions WHERE permissions_json IS NULL")
        .bindparams(permissions=DEFAULT_PERMISSIONS)
    )
    if is_sqlite:
        with op.batch_alter_table("salesperson_accounts", recreate="always") as batch:
            batch.alter_column("permissions_json", existing_type=sa.Text(), nullable=False)
    else:
        op.alter_column("salesperson_accounts", "permissions_json", existing_type=sa.Text(), nullable=False)

    insp = _state()
    t = "staff_push_subscriptions"
    cols = {c["name"] for c in insp.get_columns(t)}
    uniques = {u["name"] for u in insp.get_unique_constraints(t)}
    indexes = {i["name"] for i in insp.get_indexes(t)}
    fks = {f["name"] for f in insp.get_foreign_keys(t)}

    if is_sqlite:
        with op.batch_alter_table(t, recreate="always") as batch:
            if "uq_staff_push_subscriptions_role_endpoint_hash" in uniques:
                batch.drop_constraint("uq_staff_push_subscriptions_role_endpoint_hash", type_="unique")
            if "salesperson_account_id" not in cols:
                batch.add_column(sa.Column("salesperson_account_id", sa.Integer(), nullable=True))
            if "fk_staff_push_salesperson_account" not in fks:
                batch.create_foreign_key("fk_staff_push_salesperson_account", "salesperson_accounts",
                                         ["salesperson_account_id"], ["id"], ondelete="CASCADE")
            if "ix_staff_push_subscriptions_salesperson_account_id" not in indexes:
                batch.create_index("ix_staff_push_subscriptions_salesperson_account_id", ["salesperson_account_id"])
            if "uq_staff_push_sub_account_endpoint" not in uniques:
                batch.create_unique_constraint("uq_staff_push_sub_account_endpoint",
                                               ["staff_role", "salesperson_account_id", "endpoint_hash"])
    else:
        # MySQL reports unique constraints as indexes too.
        all_idx = uniques | indexes
        if "uq_staff_push_subscriptions_role_endpoint_hash" in all_idx:
            op.drop_constraint("uq_staff_push_subscriptions_role_endpoint_hash", t, type_="unique")
        if "salesperson_account_id" not in cols:
            op.add_column(t, sa.Column("salesperson_account_id", sa.Integer(), nullable=True))
        if "ix_staff_push_subscriptions_salesperson_account_id" not in all_idx:
            op.create_index("ix_staff_push_subscriptions_salesperson_account_id", t, ["salesperson_account_id"])
        if "fk_staff_push_salesperson_account" not in fks:
            op.create_foreign_key("fk_staff_push_salesperson_account", t, "salesperson_accounts",
                                  ["salesperson_account_id"], ["id"], ondelete="CASCADE")
        if "uq_staff_push_sub_account_endpoint" not in all_idx:
            op.create_unique_constraint("uq_staff_push_sub_account_endpoint", t,
                                        ["staff_role", "salesperson_account_id", "endpoint_hash"])

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
