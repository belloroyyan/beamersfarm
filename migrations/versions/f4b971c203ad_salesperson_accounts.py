"""Add individually managed salesperson accounts

Revision ID: f4b971c203ad
Revises: d9a17f5c0b42
Create Date: 2026-10-01 10:51:00
"""
from alembic import op
import sqlalchemy as sa

revision = "f4b971c203ad"
down_revision = "d9a17f5c0b42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "salesperson_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=40), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("username", name="uq_salesperson_accounts_username"),
    )


def downgrade():
    op.drop_table("salesperson_accounts")
