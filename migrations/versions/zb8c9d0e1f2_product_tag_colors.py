"""Store owner-selected RGB colours for product promotional tags."""
from alembic import op
import sqlalchemy as sa
revision = "zb8c9d0e1f2"
down_revision = "za7b8c9d0e1f"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("products", sa.Column("promotional_tag_color", sa.String(length=24), nullable=False, server_default="217,75,53"))
def downgrade():
    op.drop_column("products", "promotional_tag_color")
