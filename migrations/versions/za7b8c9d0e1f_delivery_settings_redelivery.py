"""Make delivery settings and redelivery schema safe on partially migrated MySQL databases.

This revision is intentionally forward-only. Earlier failed MySQL DDL may have
left some columns behind even though Alembic did not record this revision.
"""
from alembic import op
import sqlalchemy as sa


revision = "za7b8c9d0e1f"
down_revision = ("c5d6e7f809a0", "z1a2b3")
branch_labels = None
depends_on = None


DELIVERY_WINDOWS_DEFAULT = '["9:00 AM – 11:00 AM", "3:00 PM – 5:00 PM"]'
CLOSURE_CHANNELS_DEFAULT = '["push", "whatsapp", "email"]'


def _inspector():
    # Recreate the inspector after DDL so its metadata is not stale.
    return sa.inspect(op.get_bind())


def _table_exists(table_name):
    return table_name in _inspector().get_table_names()


def _columns(table_name):
    return {column["name"]: column for column in _inspector().get_columns(table_name)}


def _add_column_if_missing(table_name, column):
    if not _table_exists(table_name):
        raise RuntimeError(
            "Required table {!r} does not exist; refusing to continue migration."
            .format(table_name)
        )
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _ensure_delivery_windows_column():
    current = _columns("shop_settings")
    if "delivery_windows_json" not in current:
        # MySQL TEXT columns cannot safely use the ordinary literal DEFAULT
        # syntax used for VARCHAR columns across supported server versions.
        op.add_column(
            "shop_settings",
            sa.Column("delivery_windows_json", sa.Text(), nullable=True),
        )

    op.execute(
        sa.text(
            "UPDATE shop_settings "
            "SET delivery_windows_json = :default_value "
            "WHERE delivery_windows_json IS NULL"
        ).bindparams(default_value=DELIVERY_WINDOWS_DEFAULT)
    )

    current = _columns("shop_settings")["delivery_windows_json"]
    if current.get("nullable", True):
        op.alter_column(
            "shop_settings",
            "delivery_windows_json",
            existing_type=sa.Text(),
            existing_nullable=True,
            nullable=False,
        )


def _ensure_redelivery_table():
    table_name = "delivery_redelivery_requests"
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "order_id",
                sa.Integer(),
                sa.ForeignKey("orders.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "request_type",
                sa.String(20),
                nullable=False,
                server_default="redelivery",
            ),
            sa.Column("preferred_window", sa.String(120), nullable=True),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # A previous attempt may have created the table but stopped before creating
    # its indexes. Only create indexes that are actually absent.
    existing_indexes = {
        index["name"] for index in _inspector().get_indexes(table_name)
    }
    indexes = (
        ("ix_delivery_redelivery_requests_order_id", ["order_id"]),
        ("ix_delivery_redelivery_requests_customer_id", ["customer_id"]),
        ("ix_delivery_redelivery_requests_status", ["status"]),
    )
    for index_name, columns in indexes:
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns)


def upgrade():
    # These three columns already exist in the affected production database.
    # The checks also make this migration safe on a clean database.
    _add_column_if_missing(
        "shop_settings",
        sa.Column(
            "delivery_open_time",
            sa.String(5),
            nullable=False,
            server_default="07:00",
        ),
    )
    _add_column_if_missing(
        "shop_settings",
        sa.Column(
            "delivery_close_time",
            sa.String(5),
            nullable=False,
            server_default="19:00",
        ),
    )
    _add_column_if_missing(
        "shop_settings",
        sa.Column(
            "auto_shop_hours",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    _ensure_delivery_windows_column()

    _add_column_if_missing(
        "shop_settings",
        sa.Column(
            "closure_channels_json",
            sa.String(120),
            nullable=False,
            server_default=CLOSURE_CHANNELS_DEFAULT,
        ),
    )

    _add_column_if_missing(
        "dispatch_batches",
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    _add_column_if_missing(
        "orders",
        sa.Column("preferred_delivery_window", sa.String(120), nullable=True),
    )

    _ensure_redelivery_table()


def downgrade():
    # This migration reconciles a database that may already contain some of
    # these columns from an earlier partial run. Automatically dropping them
    # could destroy pre-existing data or schema. Use a separately reviewed
    # rollback plan if a rollback is ever required.
    pass
