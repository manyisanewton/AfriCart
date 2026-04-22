"""Add refunds table.

Revision ID: 010_add_refunds_foundation
Revises: 009_add_promotions_foundation
Create Date: 2026-04-22 01:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "010_add_refunds_foundation"
down_revision = "009_add_promotions_foundation"
branch_labels = None
depends_on = None


def upgrade():
    refund_status = sa.Enum(
        "REQUESTED",
        "APPROVED",
        "REJECTED",
        "PROCESSED",
        name="refund_status",
    )
    bind = op.get_bind()
    refund_status.create(bind, checkfirst=True)

    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", refund_status, nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"], unique=False)


def downgrade():
    op.drop_index("ix_refunds_order_id", table_name="refunds")
    op.drop_table("refunds")

    bind = op.get_bind()
    sa.Enum(name="refund_status").drop(bind, checkfirst=True)
