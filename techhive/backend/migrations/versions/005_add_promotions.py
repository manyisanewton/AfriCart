"""Add payments table.

Revision ID: 005_add_promotions
Revises: 004_add_reviews
Create Date: 2026-04-22 00:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "005_add_promotions"
down_revision = "004_add_reviews"
branch_labels = None
depends_on = None


def upgrade():
    payment_method = sa.Enum(
        "MANUAL",
        "CASH_ON_DELIVERY",
        name="payment_method",
    )
    payment_status = sa.Enum(
        "PENDING",
        "PAID",
        "FAILED",
        name="payment_status",
    )
    bind = op.get_bind()
    payment_method.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=False),
        sa.Column("method", payment_method, nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="KES"),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=False)
    op.create_index("ix_payments_reference", "payments", ["reference"], unique=False)


def downgrade():
    op.drop_index("ix_payments_reference", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")

    bind = op.get_bind()
    sa.Enum(name="payment_status").drop(bind, checkfirst=True)
    sa.Enum(name="payment_method").drop(bind, checkfirst=True)
