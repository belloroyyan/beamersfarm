"""Use requested total kg for Full Chicken standard pricing.

Revision ID: e7b5c2a41f90
Revises: d3f6b1a9c284
Create Date: 2026-10-02 19:51:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "e7b5c2a41f90"
down_revision = "d3f6b1a9c284"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE products SET unit = 'kg', price = 4500.00, "
            "description = 'A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. "
            "Choose the number of birds and enter one combined target weight in kg for the whole line; "
            "charged at the listed price per kg.' WHERE lower(name) = 'full chicken'"
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "UPDATE products SET unit = 'bird', price = 8500.00, "
            "description = 'A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. Sold per bird.' "
            "WHERE lower(name) = 'full chicken' AND unit = 'kg' AND price = 4500.00"
        )
    )
