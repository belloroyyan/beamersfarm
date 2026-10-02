"""Add owner gallery and normalize catalog pricing to units.

Revision ID: f6a8c2d4e901
Revises: e7b5c2a41f90
"""

from alembic import op
import sqlalchemy as sa

revision = "f6a8c2d4e901"
down_revision = "e7b5c2a41f90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gallery_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image", sa.String(length=160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "UPDATE products SET unit='bird', price=8500.00, "
            "description='A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. Sold per bird at the listed price.' "
            "WHERE lower(name)='full chicken'"
        )
    )


def downgrade():
    op.drop_table("gallery_images")
