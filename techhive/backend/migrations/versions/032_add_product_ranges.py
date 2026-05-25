"""add product ranges

Revision ID: 032_add_product_ranges
Revises: 031_extend_promo_codes_for_vouchers
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "032_add_product_ranges"
down_revision = "031_extend_promo_codes_for_vouchers"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_ranges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("includes_all_products", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_product_ranges_slug"),
    )
    op.create_index("ix_product_ranges_slug", "product_ranges", ["slug"], unique=False)

    op.create_table(
        "product_range_products",
        sa.Column("range_id", sa.Integer(), sa.ForeignKey("product_ranges.id"), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), primary_key=True),
    )


def downgrade():
    op.drop_table("product_range_products")
    op.drop_index("ix_product_ranges_slug", table_name="product_ranges")
    op.drop_table("product_ranges")
