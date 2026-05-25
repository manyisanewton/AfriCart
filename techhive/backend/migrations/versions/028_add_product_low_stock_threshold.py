"""add product low stock threshold

Revision ID: 028_add_product_low_stock_threshold
Revises: 027_add_product_stock_alerts
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "028_add_product_low_stock_threshold"
down_revision = "027_add_product_stock_alerts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade():
    op.drop_column("products", "low_stock_threshold")
