from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductOption(db.Model):
    __tablename__ = "product_options"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    code = db.Column(db.String(160), nullable=False, unique=True, index=True)
    type = db.Column(db.String(40), nullable=False, default="text")
    required = db.Column(db.Boolean, nullable=False, default=False)
    help_text = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
