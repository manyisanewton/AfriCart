"""add notification preferences

Revision ID: 018_add_notification_preferences
Revises: 017_add_payment_reconciliation_fields
Create Date: 2026-04-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "018_add_notification_preferences"
down_revision = "017_add_payment_reconciliation_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transactional_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("transactional_sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_notification_preferences_user_id"),
        "notification_preferences",
        ["user_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")
