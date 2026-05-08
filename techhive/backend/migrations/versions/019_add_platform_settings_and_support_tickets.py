"""add platform settings and support tickets

Revision ID: 019_add_platform_settings_and_support_tickets
Revises: 018_add_notification_preferences
Create Date: 2026-04-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "019_add_platform_settings_and_support_tickets"
down_revision = "018_add_notification_preferences"
branch_labels = None
depends_on = None


support_ticket_status = sa.Enum(
    "open",
    "in_progress",
    "resolved",
    "closed",
    name="support_ticket_status",
)


def upgrade():
    support_ticket_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_platform_settings_key"), "platform_settings", ["key"], unique=True)
    op.create_index(
        op.f("ix_platform_settings_updated_by_user_id"),
        "platform_settings",
        ["updated_by_user_id"],
        unique=False,
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="general"),
        sa.Column("status", support_ticket_status, nullable=False, server_default="open"),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_tickets_email"), "support_tickets", ["email"], unique=False)
    op.create_index(op.f("ix_support_tickets_user_id"), "support_tickets", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_email"), table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_index(op.f("ix_platform_settings_updated_by_user_id"), table_name="platform_settings")
    op.drop_index(op.f("ix_platform_settings_key"), table_name="platform_settings")
    op.drop_table("platform_settings")
    support_ticket_status.drop(op.get_bind(), checkfirst=True)
