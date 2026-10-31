from alembic import op
import sqlalchemy as sa
revision = "w4e5f6a7b8c9"
down_revision = "v3a4b5c6d7e8"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("minimum_order_quantity", sa.Numeric(12, 3), nullable=False, server_default="1.000"))
    op.create_table("product_packages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(140), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("product_package_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("package_id", sa.Integer(), sa.ForeignKey("product_packages.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False), sa.Column("quantity", sa.Numeric(12, 3), nullable=False))
    op.create_index("ix_product_package_items_package_id", "product_package_items", ["package_id"])
    op.create_index("ix_product_package_items_product_id", "product_package_items", ["product_id"])
    op.create_table("drop_shares", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("password_hash", sa.String(255), nullable=True), sa.Column("payload_kind", sa.String(12), nullable=False), sa.Column("text_content", sa.Text(), nullable=True), sa.Column("blob_content", sa.LargeBinary(), nullable=True), sa.Column("original_filename", sa.String(255), nullable=True), sa.Column("mimetype", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_drop_shares_token_hash", "drop_shares", ["token_hash"], unique=True)
    op.create_index("ix_drop_shares_created_at", "drop_shares", ["created_at"])
    op.create_index("ix_drop_shares_expires_at", "drop_shares", ["expires_at"])

def downgrade():
    op.drop_table("drop_shares")
    op.drop_table("product_package_items")
    op.drop_table("product_packages")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("minimum_order_quantity")
