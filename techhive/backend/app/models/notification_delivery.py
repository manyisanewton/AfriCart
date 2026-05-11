from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class NotificationDeliveryStatus(str, Enum):
    CREATED = "created"
    PREPARED = "prepared"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationDelivery(db.Model):
    __tablename__ = "notification_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notifications.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    channel = db.Column(
        db.Enum(NotificationChannel, name="notification_channel"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(NotificationDeliveryStatus, name="notification_delivery_status"),
        nullable=False,
    )
    recipient = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(255), nullable=True)
    template = db.Column(db.String(120), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    payload_snapshot = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    last_attempted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    notification = db.relationship("Notification", back_populates="deliveries")
    user = db.relationship("User")
