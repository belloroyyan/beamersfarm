"""Add owner-configurable analytics page selection."""
from alembic import op
import sqlalchemy as sa

revision = "q8c9d0e1f2a3"
down_revision = "p7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "shop_settings",
        sa.Column("analytics_paths", sa.String(length=2000), nullable=False, server_default="/"),
    )


def downgrade():
    op.drop_column("shop_settings", "analytics_paths")
