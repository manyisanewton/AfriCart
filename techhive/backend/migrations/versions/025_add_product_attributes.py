"""Add product attributes table.

Revision ID: 025_add_product_attributes
Revises: 024_add_product_types
Create Date: 2026-05-24 14:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "025_add_product_attributes"
down_revision = "024_add_product_types"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_attributes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("option_group_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_type_id"], ["product_types.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_attributes_product_type_id", "product_attributes", ["product_type_id"], unique=False)


def downgrade():
    op.drop_index("ix_product_attributes_product_type_id", table_name="product_attributes")
    op.drop_table("product_attributes")
