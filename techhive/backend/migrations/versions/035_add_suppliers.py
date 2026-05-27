"""add suppliers

Revision ID: 035_add_suppliers
Revises: 034_add_partners
Create Date: 2026-05-27 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "035_add_suppliers"
down_revision = "034_add_partners"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.String(length=180), nullable=False),
        sa.Column("contact_name", sa.String(length=180), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "SUSPENDED", name="supplier_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_suppliers_partner_id"), "suppliers", ["partner_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_suppliers_partner_id"), table_name="suppliers")
    op.drop_table("suppliers")
    sa.Enum(name="supplier_status").drop(op.get_bind(), checkfirst=False)
