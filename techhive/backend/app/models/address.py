from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(100), nullable=False)
    recipient_name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(30), nullable=False)
    country = db.Column(db.String(100), nullable=False, default="Kenya")
    city = db.Column(db.String(100), nullable=False)
    state_or_county = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(30), nullable=True)
    address_line_1 = db.Column(db.String(255), nullable=False)
    address_line_2 = db.Column(db.String(255), nullable=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="addresses")
