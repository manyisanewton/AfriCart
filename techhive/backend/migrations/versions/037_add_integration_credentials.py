"""add integration credentials

Revision ID: 037_add_integration_credentials
Revises: 036_add_integrations
Create Date: 2026-05-27 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "037_add_integration_credentials"
down_revision = "036_add_integrations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("integration_connections", sa.Column("credential_values", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("integration_connections", "credential_values")
