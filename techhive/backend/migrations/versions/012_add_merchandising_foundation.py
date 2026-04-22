"""Add banners and flash sales tables.

Revision ID: 012_add_merchandising_foundation
Revises: 011_add_audit_logs_foundation
Create Date: 2026-04-22 02:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_merchandising_foundation"
down_revision = "011_add_audit_logs_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column("placement", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "flash_sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_flash_sales_product_id", "flash_sales", ["product_id"], unique=False)


def downgrade():
    op.drop_index("ix_flash_sales_product_id", table_name="flash_sales")
    op.drop_table("flash_sales")
    op.drop_table("banners")
