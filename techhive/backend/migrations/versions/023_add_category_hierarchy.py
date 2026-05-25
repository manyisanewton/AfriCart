"""Add category hierarchy support.

Revision ID: 023_add_category_hierarchy
Revises: 022_add_recommendation_events
Create Date: 2026-05-24 13:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "023_add_category_hierarchy"
down_revision = "022_add_recommendation_events"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_categories_parent_id", ["parent_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_categories_parent_id_categories",
            "categories",
            ["parent_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint("fk_categories_parent_id_categories", type_="foreignkey")
        batch_op.drop_index("ix_categories_parent_id")
        batch_op.drop_column("parent_id")
