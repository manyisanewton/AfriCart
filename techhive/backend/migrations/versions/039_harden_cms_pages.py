"""harden cms pages

Revision ID: 039_harden_cms_pages
Revises: 038_add_cms_pages
Create Date: 2026-06-15 12:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "039_harden_cms_pages"
down_revision = "038_add_cms_pages"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cms_pages", sa.Column("page_key", sa.String(length=120), nullable=True))
    op.add_column("cms_pages", sa.Column("page_type", sa.String(length=40), nullable=False, server_default="custom"))
    op.add_column("cms_pages", sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"))
    op.add_column("cms_pages", sa.Column("excerpt", sa.Text(), nullable=True))
    op.add_column("cms_pages", sa.Column("meta_title", sa.String(length=255), nullable=True))
    op.add_column("cms_pages", sa.Column("meta_description", sa.Text(), nullable=True))
    op.add_column("cms_pages", sa.Column("is_system_page", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("cms_pages", sa.Column("allow_indexing", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("cms_pages", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cms_pages", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    op.add_column("cms_pages", sa.Column("updated_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "cms_pages", "users", ["created_by_user_id"], ["id"])
    op.create_foreign_key(None, "cms_pages", "users", ["updated_by_user_id"], ["id"])
    op.create_index(op.f("ix_cms_pages_page_key"), "cms_pages", ["page_key"], unique=True)
    op.create_index(op.f("ix_cms_pages_page_type"), "cms_pages", ["page_type"], unique=False)
    op.create_index(op.f("ix_cms_pages_status"), "cms_pages", ["status"], unique=False)
    op.create_index(op.f("ix_cms_pages_created_by_user_id"), "cms_pages", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_cms_pages_updated_by_user_id"), "cms_pages", ["updated_by_user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_cms_pages_updated_by_user_id"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_created_by_user_id"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_status"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_page_type"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_page_key"), table_name="cms_pages")
    op.drop_constraint(None, "cms_pages", type_="foreignkey")
    op.drop_constraint(None, "cms_pages", type_="foreignkey")
    op.drop_column("cms_pages", "updated_by_user_id")
    op.drop_column("cms_pages", "created_by_user_id")
    op.drop_column("cms_pages", "published_at")
    op.drop_column("cms_pages", "allow_indexing")
    op.drop_column("cms_pages", "is_system_page")
    op.drop_column("cms_pages", "meta_description")
    op.drop_column("cms_pages", "meta_title")
    op.drop_column("cms_pages", "excerpt")
    op.drop_column("cms_pages", "status")
    op.drop_column("cms_pages", "page_type")
    op.drop_column("cms_pages", "page_key")
