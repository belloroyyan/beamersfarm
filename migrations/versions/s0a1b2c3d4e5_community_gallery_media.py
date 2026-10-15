"""Community features and gallery media metadata."""
from alembic import op
import sqlalchemy as sa

revision = "s0a1b2c3d4e5"
down_revision = "r9d0e1f2a3b4"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("gallery_images") as batch:
        batch.add_column(sa.Column("media_type", sa.String(20), nullable=False, server_default="image"))
        batch.add_column(sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("community_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, server_default="Little notes"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image", sa.String(160), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_community_posts_customer_id", "community_posts", ["customer_id"])
    op.create_index("ix_community_posts_category", "community_posts", ["category"])
    op.create_index("ix_community_posts_status", "community_posts", ["status"])
    op.create_index("ix_community_posts_created_at", "community_posts", ["created_at"])
    op.create_table("community_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_name", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(24), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_community_comments_post_id", "community_comments", ["post_id"])
    op.create_index("ix_community_comments_customer_id", "community_comments", ["customer_id"])
    op.create_table("community_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reaction", sa.String(20), nullable=False, server_default="heart"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("post_id", "customer_id", name="uq_community_reaction_post_customer"),
    )
    op.create_index("ix_community_reactions_post_id", "community_reactions", ["post_id"])
    op.create_index("ix_community_reactions_customer_id", "community_reactions", ["customer_id"])
    op.create_table("community_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("reporter_customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_community_reports_post_id", "community_reports", ["post_id"])
    op.create_index("ix_community_reports_comment_id", "community_reports", ["comment_id"])
    op.create_index("ix_community_reports_status", "community_reports", ["status"])
    op.create_table("community_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blocker_customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("blocker_customer_id", "blocked_customer_id", name="uq_community_block_pair"),
    )
    op.create_table("community_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("community_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.String(240), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_community_notifications_customer_id", "community_notifications", ["customer_id"])
    op.create_index("ix_community_notifications_created_at", "community_notifications", ["created_at"])

def downgrade():
    op.drop_index("ix_community_notifications_created_at", table_name="community_notifications")
    op.drop_index("ix_community_notifications_customer_id", table_name="community_notifications")
    op.drop_table("community_notifications")
    op.drop_table("community_blocks")
    op.drop_index("ix_community_reports_status", table_name="community_reports")
    op.drop_index("ix_community_reports_comment_id", table_name="community_reports")
    op.drop_index("ix_community_reports_post_id", table_name="community_reports")
    op.drop_table("community_reports")
    op.drop_index("ix_community_reactions_customer_id", table_name="community_reactions")
    op.drop_index("ix_community_reactions_post_id", table_name="community_reactions")
    op.drop_table("community_reactions")
    op.drop_index("ix_community_comments_customer_id", table_name="community_comments")
    op.drop_index("ix_community_comments_post_id", table_name="community_comments")
    op.drop_table("community_comments")
    op.drop_index("ix_community_posts_created_at", table_name="community_posts")
    op.drop_index("ix_community_posts_status", table_name="community_posts")
    op.drop_index("ix_community_posts_category", table_name="community_posts")
    op.drop_index("ix_community_posts_customer_id", table_name="community_posts")
    op.drop_table("community_posts")
    with op.batch_alter_table("gallery_images") as batch:
        batch.drop_column("pinned")
        batch.drop_column("media_type")
