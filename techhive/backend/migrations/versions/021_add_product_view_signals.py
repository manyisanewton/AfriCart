"""add product view signals

Revision ID: 021_add_product_view_signals
Revises: 020_add_notification_deliveries
Create Date: 2026-04-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "021_add_product_view_signals"
down_revision = "020_add_notification_deliveries"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_product_views_user_product"),
    )
    op.create_index(op.f("ix_product_views_user_id"), "product_views", ["user_id"], unique=False)
    op.create_index(op.f("ix_product_views_product_id"), "product_views", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_views_last_viewed_at"), "product_views", ["last_viewed_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_product_views_last_viewed_at"), table_name="product_views")
    op.drop_index(op.f("ix_product_views_product_id"), table_name="product_views")
    op.drop_index(op.f("ix_product_views_user_id"), table_name="product_views")
    op.drop_table("product_views")
