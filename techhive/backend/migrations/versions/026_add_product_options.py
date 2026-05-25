"""add product options

Revision ID: 026_add_product_options
Revises: 025_add_product_attributes
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "026_add_product_options"
down_revision = "025_add_product_attributes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("help_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_options_code", "product_options", ["code"], unique=True)


def downgrade():
    op.drop_index("ix_product_options_code", table_name="product_options")
    op.drop_table("product_options")
