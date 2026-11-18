"""Merge the owner-managed payment accounts and team-members heads.

Revision ID: bf20261118merge
Revises: c8d9e0f1a2b3, bf20261117merge
Create Date: 2026-11-18

This is a history-only merge. Both parent revisions retain their own schema
changes; this revision deliberately performs no additional DDL.
"""
revision = "bf20261118merge"
down_revision = ("c8d9e0f1a2b3", "bf20261117merge")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
