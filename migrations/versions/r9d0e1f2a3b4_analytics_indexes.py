"""Index analytics dimensions used by owner reporting."""
from alembic import op

revision = "r9d0e1f2a3b4"
down_revision = "q8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_path", "analytics_events", ["path"])


def downgrade():
    op.drop_index("ix_analytics_events_path", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
