"""Merge the logistics workflow and operational index migration branches.

Revision ID: d6e7f8a9b0c1
Revises: c9d8e7f6a5b4, bf20261106
"""

revision = "d6e7f8a9b0c1"
down_revision = ("c9d8e7f6a5b4", "bf20261106")
branch_labels = None
depends_on = None


def upgrade():
    # Both parent migrations have already applied their own schema changes.
    # This revision only joins the Alembic history branches.
    pass


def downgrade():
    # A merge-only revision has no schema changes to reverse.
    pass
