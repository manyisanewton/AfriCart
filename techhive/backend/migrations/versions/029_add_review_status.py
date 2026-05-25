"""add review moderation status

Revision ID: 029_add_review_status
Revises: 028_add_product_low_stock_threshold
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "029_add_review_status"
down_revision = "028_add_product_low_stock_threshold"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "reviews",
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("reviews", "status")
