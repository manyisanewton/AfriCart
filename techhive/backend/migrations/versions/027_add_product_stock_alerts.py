"""add product stock alerts

Revision ID: 027_add_product_stock_alerts
Revises: 026_add_product_options
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "027_add_product_stock_alerts"
down_revision = "026_add_product_options"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_stock_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_stock_alerts_product_id", "product_stock_alerts", ["product_id"], unique=True)


def downgrade():
    op.drop_index("ix_product_stock_alerts_product_id", table_name="product_stock_alerts")
    op.drop_table("product_stock_alerts")
