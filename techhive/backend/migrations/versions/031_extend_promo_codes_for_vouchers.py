"""extend promo codes for vouchers

Revision ID: 031_extend_promo_codes_for_vouchers
Revises: 030_add_offers_foundation
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "031_extend_promo_codes_for_vouchers"
down_revision = "030_add_offers_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "promo_codes",
        sa.Column("name", sa.String(length=160), nullable=False, server_default=""),
    )
    op.add_column(
        "promo_codes",
        sa.Column("usage", sa.String(length=40), nullable=False, server_default="Single use"),
    )
    op.create_table(
        "promo_code_offers",
        sa.Column("promo_code_id", sa.Integer(), sa.ForeignKey("promo_codes.id"), primary_key=True),
        sa.Column("offer_id", sa.Integer(), sa.ForeignKey("offers.id"), primary_key=True),
    )


def downgrade():
    op.drop_table("promo_code_offers")
    op.drop_column("promo_codes", "usage")
    op.drop_column("promo_codes", "name")
