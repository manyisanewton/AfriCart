from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    in_app_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    sms_enabled = db.Column(db.Boolean, nullable=False, default=False)
    transactional_email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    transactional_sms_enabled = db.Column(db.Boolean, nullable=False, default=False)
    marketing_email_enabled = db.Column(db.Boolean, nullable=False, default=False)
    marketing_sms_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="notification_preference")
