"""add cms pages

Revision ID: 038_add_cms_pages
Revises: 037_add_integration_credentials
Create Date: 2026-05-27 17:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "038_add_cms_pages"
down_revision = "037_add_integration_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cms_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("registration_required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_pages_url"), "cms_pages", ["url"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_cms_pages_url"), table_name="cms_pages")
    op.drop_table("cms_pages")
