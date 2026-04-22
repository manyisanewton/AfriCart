from flask import g, jsonify

from app.blueprints.notifications import notifications_bp
from app.blueprints.notifications.push import mark_notification_read
from app.middleware.auth_required import auth_required
from app.models import Notification


def serialize_notification(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "type": notification.type.value,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
    }


@notifications_bp.get("")
@auth_required
def list_notifications():
    """
    List the authenticated user's notifications.
    ---
    tags:
      - Notifications
    responses:
      200:
        description: Notifications list.
    """
    notifications = (
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    unread_count = sum(0 if notification.is_read else 1 for notification in notifications)
    return jsonify(
        {
            "items": [serialize_notification(notification) for notification in notifications],
            "summary": {"unread_count": unread_count, "total": len(notifications)},
        }
    )


@notifications_bp.post("/<int:notification_id>/read")
@auth_required
def mark_single_notification_read(notification_id: int):
    """
    Mark a notification as read.
    ---
    tags:
      - Notifications
    responses:
      200:
        description: Notification marked as read.
      404:
        description: Notification not found.
    """
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=g.current_user.id,
    ).first()
    if notification is None:
        return jsonify({"error": {"code": "not_found", "message": "Notification not found."}}), 404

    mark_notification_read(notification)
    from app.extensions import db
    db.session.commit()
    return jsonify({"item": serialize_notification(notification)})


@notifications_bp.post("/read-all")
@auth_required
def mark_all_notifications_read():
    """
    Mark all of the authenticated user's notifications as read.
    ---
    tags:
      - Notifications
    responses:
      200:
        description: Notifications marked as read.
    """
    notifications = Notification.query.filter_by(user_id=g.current_user.id, is_read=False).all()
    for notification in notifications:
        mark_notification_read(notification)
    from app.extensions import db
    db.session.commit()
    return jsonify({"updated_count": len(notifications)})
