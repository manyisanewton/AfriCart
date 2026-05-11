"""add recommendation events

Revision ID: 022_add_recommendation_events
Revises: 021_add_product_view_signals
Create Date: 2026-04-28 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "022_add_recommendation_events"
down_revision = "021_add_product_view_signals"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_events_user_id"), "recommendation_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_product_id"), "recommendation_events", ["product_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_event_type"), "recommendation_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_recommendation_events_mode"), "recommendation_events", ["mode"], unique=False)
    op.create_index(op.f("ix_recommendation_events_reason_code"), "recommendation_events", ["reason_code"], unique=False)
    op.create_index(op.f("ix_recommendation_events_created_at"), "recommendation_events", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_recommendation_events_created_at"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_reason_code"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_mode"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_event_type"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_product_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_user_id"), table_name="recommendation_events")
    op.drop_table("recommendation_events")
