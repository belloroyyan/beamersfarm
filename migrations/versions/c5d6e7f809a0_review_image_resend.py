"""Add review image attachments and finalize Resend email configuration."""
from alembic import op
import sqlalchemy as sa
revision = "c5d6e7f809a0"
down_revision = "b4c5d6e7f809"
branch_labels = None
depends_on = None
def upgrade(): op.add_column("reviews", sa.Column("image", sa.String(length=255), nullable=True))
def downgrade(): op.drop_column("reviews", "image")
