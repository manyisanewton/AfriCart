"""Add payment failure tracking fields.

Revision ID: 016_add_payment_failure_tracking
Revises: 015_harden_mpesa_payment_processing
Create Date: 2026-04-23 12:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "016_add_payment_failure_tracking"
down_revision = "015_harden_mpesa_payment_processing"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("failure_code", sa.String(length=80), nullable=True))
    op.add_column("payments", sa.Column("failure_message", sa.String(length=255), nullable=True))
    op.create_index("ix_payments_failure_code", "payments", ["failure_code"], unique=False)


def downgrade():
    op.drop_index("ix_payments_failure_code", table_name="payments")
    op.drop_column("payments", "failure_message")
    op.drop_column("payments", "failure_code")
