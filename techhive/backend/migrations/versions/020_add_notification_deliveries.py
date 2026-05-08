"""add notification deliveries

Revision ID: 020_add_notification_deliveries
Revises: 019_add_platform_settings_and_support_tickets
Create Date: 2026-04-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "020_add_notification_deliveries"
down_revision = "019_add_platform_settings_and_support_tickets"
branch_labels = None
depends_on = None


notification_channel = sa.Enum("in_app", "email", "sms", name="notification_channel")
notification_delivery_status = sa.Enum(
    "created",
    "prepared",
    "queued",
    "sent",
    "failed",
    "skipped",
    name="notification_delivery_status",
)


def upgrade():
    bind = op.get_bind()
    notification_channel.create(bind, checkfirst=True)
    notification_delivery_status.create(bind, checkfirst=True)

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("status", notification_delivery_status, nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("template", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("payload_snapshot", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_deliveries_notification_id"),
        "notification_deliveries",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_deliveries_user_id"),
        "notification_deliveries",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_notification_deliveries_user_id"), table_name="notification_deliveries")
    op.drop_index(op.f("ix_notification_deliveries_notification_id"), table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    bind = op.get_bind()
    notification_delivery_status.drop(bind, checkfirst=True)
    notification_channel.drop(bind, checkfirst=True)
