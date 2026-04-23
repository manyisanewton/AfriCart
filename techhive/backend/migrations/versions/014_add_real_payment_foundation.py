"""Add real payment foundation fields.

Revision ID: 014_add_real_payment_foundation
Revises: 013_add_vendor_kyc_foundation
Create Date: 2026-04-23 11:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "014_add_real_payment_foundation"
down_revision = "013_add_vendor_kyc_foundation"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for value in ["MPESA", "STRIPE", "FLUTTERWAVE", "PAYPAL"]:
            op.execute(f"ALTER TYPE payment_method ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("payments", sa.Column("external_reference", sa.String(length=120), nullable=True))
    op.add_column("payments", sa.Column("provider_event_id", sa.String(length=120), nullable=True))
    op.add_column("payments", sa.Column("redirect_url", sa.String(length=500), nullable=True))
    op.create_index("ix_payments_external_reference", "payments", ["external_reference"], unique=True)
    op.create_index("ix_payments_provider_event_id", "payments", ["provider_event_id"], unique=True)


def downgrade():
    op.drop_index("ix_payments_provider_event_id", table_name="payments")
    op.drop_index("ix_payments_external_reference", table_name="payments")
    op.drop_column("payments", "redirect_url")
    op.drop_column("payments", "provider_event_id")
    op.drop_column("payments", "external_reference")
