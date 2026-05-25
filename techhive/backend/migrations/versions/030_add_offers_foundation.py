"""add offers foundation

Revision ID: 030_add_offers_foundation
Revises: 029_add_review_status
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "030_add_offers_foundation"
down_revision = "029_add_review_status"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "offer_conditions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("range_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("proxy_class", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "offer_benefits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("range_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("proxy_class", sa.String(length=120), nullable=True),
        sa.Column("max_affected_items", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("offer_type", sa.String(length=80), nullable=False),
        sa.Column("exclusive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Open"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("num_applications", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("num_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("condition_id", sa.Integer(), sa.ForeignKey("offer_conditions.id"), nullable=True),
        sa.Column("benefit_id", sa.Integer(), sa.ForeignKey("offer_benefits.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_offers_slug"),
    )
    op.create_index("ix_offers_slug", "offers", ["slug"], unique=False)


def downgrade():
    op.drop_index("ix_offers_slug", table_name="offers")
    op.drop_table("offers")
    op.drop_table("offer_benefits")
    op.drop_table("offer_conditions")
