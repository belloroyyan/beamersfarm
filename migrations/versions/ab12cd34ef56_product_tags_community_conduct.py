"""Product promotional tags and community conduct rules."""
from alembic import op
import sqlalchemy as sa

revision = "ab12cd34ef56"
down_revision = "za7b8c9d0e1f"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("promotional_tag", sa.String(length=40), nullable=False, server_default=""))
    op.create_table(
        "community_conduct_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

def downgrade():
    op.drop_table("community_conduct_rules")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("promotional_tag")
