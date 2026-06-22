from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class CmsPage(db.Model):
    __tablename__ = "cms_pages"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False, unique=True, index=True)
    page_key = db.Column(db.String(120), nullable=True, unique=True, index=True)
    page_type = db.Column(db.String(40), nullable=False, default="custom", index=True)
    status = db.Column(db.String(40), nullable=False, default="draft", index=True)
    title = db.Column(db.String(255), nullable=False)
    excerpt = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False, default="")
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    registration_required = db.Column(db.Boolean, nullable=False, default=False)
    is_system_page = db.Column(db.Boolean, nullable=False, default=False)
    allow_indexing = db.Column(db.Boolean, nullable=False, default=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    updated_by_user = db.relationship("User", foreign_keys=[updated_by_user_id], lazy="selectin")
