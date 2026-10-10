"""Add coupons, privacy rules and coupon metadata."""
from alembic import op
import sqlalchemy as sa
revision="n6a7b8c9d0e1"
down_revision="m5f6a7b8c9d0"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("orders",sa.Column("coupon_code",sa.String(40),nullable=True)); op.add_column("orders",sa.Column("discount_amount",sa.Numeric(12,2),nullable=False,server_default="0"))
    op.create_table("coupons",sa.Column("id",sa.Integer(),nullable=False),sa.Column("code",sa.String(40),nullable=False),sa.Column("discount_type",sa.String(12),nullable=False,server_default="percent"),sa.Column("value",sa.Numeric(12,2),nullable=False),sa.Column("minimum_spend",sa.Numeric(12,2),nullable=False,server_default="0"),sa.Column("max_uses",sa.Integer(),nullable=True),sa.Column("uses",sa.Integer(),nullable=False,server_default="0"),sa.Column("excluded_product_ids",sa.String(500),nullable=False,server_default=""),sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("starts_at",sa.DateTime(),nullable=True),sa.Column("ends_at",sa.DateTime(),nullable=True),sa.Column("created_at",sa.DateTime(),nullable=False),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("code")); op.create_index("ix_coupons_code","coupons",["code"])
    op.create_table("privacy_rules",sa.Column("id",sa.Integer(),nullable=False),sa.Column("title",sa.String(160),nullable=False),sa.Column("body",sa.Text(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("sort_order",sa.Integer(),nullable=False,server_default="0"),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.PrimaryKeyConstraint("id"))
def downgrade():
    op.drop_table("privacy_rules"); op.drop_index("ix_coupons_code",table_name="coupons"); op.drop_table("coupons"); op.drop_column("orders","discount_amount"); op.drop_column("orders","coupon_code")
