"""Add payment reconciliation lifecycle fields.

Revision ID: 017_add_payment_reconciliation_fields
Revises: 016_add_payment_failure_tracking
Create Date: 2026-04-23 13:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "017_add_payment_reconciliation_fields"
down_revision = "016_add_payment_failure_tracking"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "payments",
        sa.Column("reconciliation_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("reconciliation_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_payments_initiated_at", "payments", ["initiated_at"], unique=False)
    op.create_index(
        "ix_payments_reconciliation_due_at",
        "payments",
        ["reconciliation_due_at"],
        unique=False,
    )
    op.alter_column("payments", "reconciliation_attempts", server_default=None)


def downgrade():
    op.drop_index("ix_payments_reconciliation_due_at", table_name="payments")
    op.drop_index("ix_payments_initiated_at", table_name="payments")
    op.drop_column("payments", "reconciliation_attempts")
    op.drop_column("payments", "reconciliation_due_at")
    op.drop_column("payments", "initiated_at")
