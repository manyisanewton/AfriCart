"""Harden payment processing fields.

Revision ID: 015_harden_mpesa_payment_processing
Revises: 014_add_real_payment_foundation
Create Date: 2026-04-23 12:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "015_harden_mpesa_payment_processing"
down_revision = "014_add_real_payment_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("payer_phone_number", sa.String(length=30), nullable=True))
    op.add_column("payments", sa.Column("provider_receipt", sa.String(length=120), nullable=True))
    op.add_column("payments", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_payments_provider_receipt", "payments", ["provider_receipt"], unique=True)


def downgrade():
    op.drop_index("ix_payments_provider_receipt", table_name="payments")
    op.drop_column("payments", "processed_at")
    op.drop_column("payments", "provider_receipt")
    op.drop_column("payments", "payer_phone_number")
