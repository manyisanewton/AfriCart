"""Add delivery zones, agents, and order delivery fields.

Revision ID: 008_add_delivery_foundation
Revises: 007_add_notifications_foundation
Create Date: 2026-04-22 01:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "008_add_delivery_foundation"
down_revision = "007_add_notifications_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("estimated_days_min", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estimated_days_max", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("city"),
    )
    op.create_index("ix_delivery_zones_city", "delivery_zones", ["city"], unique=False)

    op.create_table(
        "delivery_agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )

    op.add_column("orders", sa.Column("delivery_status", sa.String(length=40), nullable=False, server_default="processing"))
    op.add_column("orders", sa.Column("tracking_token", sa.String(length=64), nullable=False, server_default="pending-token"))
    op.add_column("orders", sa.Column("delivery_zone_name", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("delivery_agent_id", sa.Integer(), nullable=True))
    op.create_index("ix_orders_tracking_token", "orders", ["tracking_token"], unique=True)
    op.create_index("ix_orders_delivery_agent_id", "orders", ["delivery_agent_id"], unique=False)
    op.create_foreign_key(
        "fk_orders_delivery_agent_id",
        "orders",
        "delivery_agents",
        ["delivery_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_orders_delivery_agent_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_delivery_agent_id", table_name="orders")
    op.drop_index("ix_orders_tracking_token", table_name="orders")
    op.drop_column("orders", "delivery_agent_id")
    op.drop_column("orders", "delivery_zone_name")
    op.drop_column("orders", "tracking_token")
    op.drop_column("orders", "delivery_status")
    op.drop_table("delivery_agents")
    op.drop_index("ix_delivery_zones_city", table_name="delivery_zones")
    op.drop_table("delivery_zones")
