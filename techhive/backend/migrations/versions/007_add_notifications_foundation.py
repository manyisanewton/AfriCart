"""Add notifications table.

Revision ID: 007_add_notifications_foundation
Revises: 006_add_reviews_foundation
Create Date: 2026-04-22 01:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "007_add_notifications_foundation"
down_revision = "006_add_reviews_foundation"
branch_labels = None
depends_on = None


def upgrade():
    notification_type = sa.Enum(
        "ORDER_CREATED",
        "ORDER_CANCELLED",
        "PAYMENT_CREATED",
        "PAYMENT_PAID",
        "PAYMENT_FAILED",
        name="notification_type",
    )
    bind = op.get_bind()
    notification_type.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    bind = op.get_bind()
    sa.Enum(name="notification_type").drop(bind, checkfirst=True)
