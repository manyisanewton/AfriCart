from datetime import datetime, timezone

from app.extensions import db
from app.models import Notification, NotificationType


def create_notification(user_id: int, notification_type: NotificationType, title: str, message: str):
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
    )
    db.session.add(notification)
    return notification


def mark_notification_read(notification: Notification):
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
