"""Add vendor KYC submissions table.

Revision ID: 013_add_vendor_kyc_foundation
Revises: 012_add_merchandising_foundation
Create Date: 2026-04-23 10:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "013_add_vendor_kyc_foundation"
down_revision = "012_add_merchandising_foundation"
branch_labels = None
depends_on = None


def upgrade():
    vendor_kyc_status = sa.Enum(
        "NOT_SUBMITTED",
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="vendor_kyc_status",
    )
    bind = op.get_bind()
    vendor_kyc_status.create(bind, checkfirst=True)

    op.create_table(
        "vendor_kyc_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("legal_business_name", sa.String(length=200), nullable=False),
        sa.Column("registration_number", sa.String(length=120), nullable=False),
        sa.Column("tax_id", sa.String(length=120), nullable=True),
        sa.Column("contact_person_name", sa.String(length=200), nullable=False),
        sa.Column("contact_person_id_number", sa.String(length=120), nullable=False),
        sa.Column("document_url", sa.String(length=500), nullable=False),
        sa.Column("status", vendor_kyc_status, nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("vendor_id", name="uq_vendor_kyc_submission_vendor_id"),
    )
    op.create_index(
        "ix_vendor_kyc_submissions_vendor_id",
        "vendor_kyc_submissions",
        ["vendor_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_vendor_kyc_submissions_vendor_id", table_name="vendor_kyc_submissions")
    op.drop_table("vendor_kyc_submissions")

    bind = op.get_bind()
    sa.Enum(name="vendor_kyc_status").drop(bind, checkfirst=True)
