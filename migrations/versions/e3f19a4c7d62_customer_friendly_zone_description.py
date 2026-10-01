"""Replace the internal seed note with customer-facing delivery guidance.

Revision ID: e3f19a4c7d62
Revises: f4b971c203ad
Create Date: 2026-10-01 11:01:30
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f19a4c7d62"
down_revision = "f4b971c203ad"
branch_labels = None
depends_on = None

OLD_DESCRIPTION = "Default zone using the existing delivery fee. Edit the included areas and price in the owner panel."
NEW_DESCRIPTION = "Standard Osogbo delivery tier. Please confirm with us if you are unsure whether your neighborhood is included."


def upgrade():
    op.execute(
        sa.text(
            "UPDATE delivery_zones SET description = :new_description "
            "WHERE name = :zone_name AND description = :old_description"
        ).bindparams(
            new_description=NEW_DESCRIPTION,
            zone_name="Osogbo — Standard delivery",
            old_description=OLD_DESCRIPTION,
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "UPDATE delivery_zones SET description = :old_description "
            "WHERE name = :zone_name AND description = :new_description"
        ).bindparams(
            old_description=OLD_DESCRIPTION,
            zone_name="Osogbo — Standard delivery",
            new_description=NEW_DESCRIPTION,
        )
    )
