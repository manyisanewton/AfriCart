"""Add product types table.

Revision ID: 024_add_product_types
Revises: 023_add_category_hierarchy
Create Date: 2026-05-24 13:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "024_add_product_types"
down_revision = "023_add_category_hierarchy"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("requires_shipping", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("track_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_product_types_slug", "product_types", ["slug"], unique=False)


def downgrade():
    op.drop_index("ix_product_types_slug", table_name="product_types")
    op.drop_table("product_types")
