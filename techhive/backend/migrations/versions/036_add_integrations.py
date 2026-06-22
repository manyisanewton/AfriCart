"""add integrations

Revision ID: 036_add_integrations
Revises: 035_add_suppliers
Create Date: 2026-05-27 13:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "036_add_integrations"
down_revision = "035_add_suppliers"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=True),
        sa.Column("connection_type", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("auth_type", sa.String(length=80), nullable=False),
        sa.Column("credential_source", sa.String(length=80), nullable=False),
        sa.Column("secret_env_prefix", sa.String(length=120), nullable=True),
        sa.Column("default_company", sa.String(length=160), nullable=True),
        sa.Column("default_warehouse", sa.String(length=160), nullable=True),
        sa.Column("poll_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_connections_connection_type"), "integration_connections", ["connection_type"], unique=False)
    op.create_index(op.f("ix_integration_connections_partner_id"), "integration_connections", ["partner_id"], unique=False)
    op.create_table(
        "integration_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("connection_name", sa.String(length=160), nullable=False),
        sa.Column("direction", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload_excerpt", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_logs_connection_id"), "integration_logs", ["connection_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_integration_logs_connection_id"), table_name="integration_logs")
    op.drop_table("integration_logs")
    op.drop_index(op.f("ix_integration_connections_partner_id"), table_name="integration_connections")
    op.drop_index(op.f("ix_integration_connections_connection_type"), table_name="integration_connections")
    op.drop_table("integration_connections")
