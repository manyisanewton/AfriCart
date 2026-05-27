"""add partners

Revision ID: 034_add_partners
Revises: 033_add_user_must_change_password
Create Date: 2026-05-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "034_add_partners"
down_revision = "033_add_user_must_change_password"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_partners_code"), "partners", ["code"], unique=True)
    op.create_table(
        "partner_users",
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("partner_id", "user_id"),
    )


def downgrade():
    op.drop_table("partner_users")
    op.drop_index(op.f("ix_partners_code"), table_name="partners")
    op.drop_table("partners")
