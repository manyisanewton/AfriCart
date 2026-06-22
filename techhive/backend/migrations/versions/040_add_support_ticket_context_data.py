"""add support ticket context data

Revision ID: 040_add_support_ticket_context_data
Revises: 039_harden_cms_pages
Create Date: 2026-06-15 12:52:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "040_add_support_ticket_context_data"
down_revision = "039_harden_cms_pages"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("support_tickets", sa.Column("context_data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("support_tickets", "context_data")
