"""add delivery pricing fields

Revision ID: 042_add_delivery_pricing_fields
Revises: 041_add_guest_checkout_order_fields
Create Date: 2026-06-22 21:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "042_add_delivery_pricing_fields"
down_revision = "041_add_guest_checkout_order_fields"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("weight_grams", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dimensions_text", sa.String(length=120), nullable=True))

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("delivery_location_label", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("delivery_latitude", sa.Numeric(precision=10, scale=7), nullable=True))
        batch_op.add_column(sa.Column("delivery_longitude", sa.Numeric(precision=10, scale=7), nullable=True))
        batch_op.add_column(sa.Column("delivery_distance_km", sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column("shipping_weight_grams", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("shipping_weight_grams")
        batch_op.drop_column("delivery_distance_km")
        batch_op.drop_column("delivery_longitude")
        batch_op.drop_column("delivery_latitude")
        batch_op.drop_column("delivery_location_label")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("dimensions_text")
        batch_op.drop_column("weight_grams")
