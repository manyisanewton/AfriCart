"""add guest checkout order fields

Revision ID: 041_add_guest_checkout_order_fields
Revises: 040_add_support_ticket_context_data
Create Date: 2026-06-22 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "041_add_guest_checkout_order_fields"
down_revision = "040_add_support_ticket_context_data"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("guest_email", sa.String(length=255), nullable=True))
        batch_op.create_index(batch_op.f("ix_orders_guest_email"), ["guest_email"], unique=False)


def downgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_guest_email"))
        batch_op.drop_column("guest_email")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
