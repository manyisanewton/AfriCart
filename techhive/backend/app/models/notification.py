from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationType(str, Enum):
    ORDER_CREATED = "order_created"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_CREATED = "payment_created"
    PAYMENT_PAID = "payment_paid"
    PAYMENT_FAILED = "payment_failed"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(
        db.Enum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="notifications")
