"""Add in-person sales and database-backed overlay state."""
from alembic import op
import sqlalchemy as sa
revision="v3a4b5c6d7e8";down_revision="u2f4a7c9e613";branch_labels=None;depends_on=None
def upgrade():
 with op.batch_alter_table("coupons") as b:b.add_column(sa.Column("gift_viewed_at",sa.DateTime(),nullable=True))
 with op.batch_alter_table("orders") as b:b.add_column(sa.Column("order_channel",sa.String(20),nullable=False,server_default="website"));b.add_column(sa.Column("recorded_by",sa.String(120),nullable=True));b.create_index("ix_orders_order_channel",["order_channel"])
 with op.batch_alter_table("partner_listings") as b:b.add_column(sa.Column("invite_id",sa.Integer(),sa.ForeignKey("partner_ad_invites.id",name="fk_partner_listings_invite_id",ondelete="SET NULL"),nullable=True));b.create_index("ix_partner_listings_invite_id",["invite_id"])
 with op.batch_alter_table("partner_ad_invites") as b:b.add_column(sa.Column("push_endpoint",sa.Text(),nullable=True));b.add_column(sa.Column("push_p256dh",sa.String(200),nullable=True));b.add_column(sa.Column("push_auth",sa.String(200),nullable=True));b.add_column(sa.Column("push_endpoint_hash",sa.String(64),nullable=True));b.create_index("ix_partner_ad_invites_push_endpoint_hash",["push_endpoint_hash"],unique=True)
 op.create_table("site_overlay_seen",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("visitor_key",sa.String(64),nullable=True),sa.Column("customer_id",sa.Integer(),sa.ForeignKey("customers.id",ondelete="CASCADE"),nullable=True),sa.Column("overlay_type",sa.String(32),nullable=False),sa.Column("object_id",sa.Integer(),nullable=False),sa.Column("seen_at",sa.DateTime(),nullable=False));op.create_index("ix_site_overlay_seen_visitor_key","site_overlay_seen",["visitor_key"]);op.create_index("ix_site_overlay_seen_customer_id","site_overlay_seen",["customer_id"]);op.create_index("uq_site_overlay_seen_identity","site_overlay_seen",["visitor_key","customer_id","overlay_type","object_id"],unique=True)
def downgrade():pass
