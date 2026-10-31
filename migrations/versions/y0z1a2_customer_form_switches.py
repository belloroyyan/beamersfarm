"""independent customer form availability switches
Revision ID: y0z1a2
Revises: x9y0z1
"""
from alembic import op
import sqlalchemy as sa
revision="y0z1a2"
down_revision="x9y0z1"
branch_labels=None
depends_on=None
def upgrade():
    for name in ("wholesale_open","customer_care_open","reviews_open","registration_open","partner_forms_open"):
        op.add_column("shop_settings",sa.Column(name,sa.Boolean(),nullable=False,server_default=sa.true()))
def downgrade():
    for name in ("partner_forms_open","registration_open","reviews_open","customer_care_open","wholesale_open"):
        op.drop_column("shop_settings",name)
