"""Add promo codes and order discount fields.

Revision ID: 009_add_promotions_foundation
Revises: 008_add_delivery_foundation
Create Date: 2026-04-22 01:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "009_add_promotions_foundation"
down_revision = "008_add_delivery_foundation"
branch_labels = None
depends_on = None


def upgrade():
    promo_code_type = sa.Enum(
        "PERCENTAGE",
        "FIXED",
        name="promo_code_type",
    )
    bind = op.get_bind()
    promo_code_type.create(bind, checkfirst=True)

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", promo_code_type, nullable=False),
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("minimum_order_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=False)

    op.add_column("orders", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("promo_code", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("orders", "promo_code")
    op.drop_column("orders", "discount_amount")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")

    bind = op.get_bind()
    sa.Enum(name="promo_code_type").drop(bind, checkfirst=True)
