"""Add product image galleries, helpful review votes and delivery blackout rules."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "f7a9c2d4e610"
down_revision = ("u2f4a7c9e613", "e1f2a3b4c5d6")
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    settings_columns = {c["name"] for c in inspector.get_columns("shop_settings")}
    if "delivery_blackouts_json" not in settings_columns:
        op.add_column("shop_settings", sa.Column(
            "delivery_blackouts_json", sa.Text(), nullable=False,
            server_default='{"dates":[],"weekdays":[]}'
        ))
    tables = set(inspector.get_table_names())
    if "product_images" not in tables:
        op.create_table(
            "product_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("image_path", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
    if "review_helpful" not in tables:
        op.create_table(
            "review_helpful",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("review_id", "customer_id", name="uq_review_helpful_customer"),
        )
        op.create_index("ix_review_helpful_review_id", "review_helpful", ["review_id"])
        op.create_index("ix_review_helpful_customer_id", "review_helpful", ["customer_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "review_helpful" in tables:
        op.drop_table("review_helpful")
    if "product_images" in tables:
        op.drop_table("product_images")
    cols = {c["name"] for c in inspect(bind).get_columns("shop_settings")}
    if "delivery_blackouts_json" in cols:
        op.drop_column("shop_settings", "delivery_blackouts_json")
