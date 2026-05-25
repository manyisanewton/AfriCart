"""add user must_change_password flag

Revision ID: 033_add_user_must_change_password
Revises: 032_add_product_ranges
Create Date: 2026-05-24 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "033_add_user_must_change_password"
down_revision = "032_add_product_ranges"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("must_change_password")
