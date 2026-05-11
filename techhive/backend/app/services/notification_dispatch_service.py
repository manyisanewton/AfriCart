from __future__ import annotations

import json
from flask import current_app

from app.extensions import db
from app.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationPreference,
    NotificationType,
    User,
)
from app.services.email_service import send_email


DEFAULT_CHANNELS = {"in_app", "email", "sms"}


def get_or_create_notification_preferences(user: User) -> NotificationPreference:
    preferences = user.notification_preference
    if preferences is None:
        preferences = NotificationPreference(user_id=user.id)
        db.session.add(preferences)
        db.session.flush()
    return preferences


def update_notification_preferences(user: User, payload: dict) -> NotificationPreference:
    preferences = get_or_create_notification_preferences(user)
    for field in payload["provided_fields"]:
        setattr(preferences, field, payload[field])
    return preferences


def _channel_allowed(preferences: NotificationPreference, channel: str, *, is_marketing: bool) -> bool:
    if channel == "in_app":
        return preferences.in_app_enabled
    if channel == "email":
        return preferences.email_enabled and (
            preferences.marketing_email_enabled
            if is_marketing
            else preferences.transactional_email_enabled
        )
    if channel == "sms":
        return preferences.sms_enabled and (
            preferences.marketing_sms_enabled
            if is_marketing
            else preferences.transactional_sms_enabled
        )
    return False


def _normalize_delivery_status(status: str | None) -> NotificationDeliveryStatus:
    mapping = {
        "created": NotificationDeliveryStatus.CREATED,
        "prepared": NotificationDeliveryStatus.PREPARED,
        "queued": NotificationDeliveryStatus.QUEUED,
        "sent": NotificationDeliveryStatus.SENT,
        "failed": NotificationDeliveryStatus.FAILED,
        "skipped": NotificationDeliveryStatus.SKIPPED,
    }
    return mapping.get((status or "").lower(), NotificationDeliveryStatus.FAILED)


def _record_delivery(
    *,
    user: User,
    notification,
    channel: NotificationChannel,
    result: dict,
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        notification_id=notification.id if notification is not None else None,
        user_id=user.id,
        channel=channel,
        status=_normalize_delivery_status(result.get("status")),
        recipient=result.get("recipient"),
        subject=result.get("subject"),
        template=result.get("template"),
        category=result.get("category"),
        reason=result.get("reason"),
        payload_snapshot=json.dumps(result, sort_keys=True),
        retry_count=result.get("retry_count", 0),
        last_attempted_at=db.func.now(),
    )
    db.session.add(delivery)
    db.session.flush()
    return delivery


def dispatch_user_notification(
    *,
    user: User,
    notification_type: NotificationType,
    title: str,
    message: str,
    email_subject: str | None = None,
    email_template: str | None = None,
    email_context: dict | None = None,
    sms_message: str | None = None,
    is_marketing: bool = False,
    channels: set[str] | None = None,
) -> dict:
    preferences = get_or_create_notification_preferences(user)
    selected_channels = set(channels or DEFAULT_CHANNELS)
    deliveries: dict[str, dict] = {}
    notification = None

    if "in_app" in selected_channels:
        if _channel_allowed(preferences, "in_app", is_marketing=is_marketing):
            from app.blueprints.notifications.push import create_notification

            notification = create_notification(user.id, notification_type, title, message)
            deliveries["in_app"] = {"channel": "in_app", "status": "created", "recipient": str(user.id)}
        else:
            deliveries["in_app"] = {
                "channel": "in_app",
                "status": "skipped",
                "reason": "preference_disabled",
                "recipient": str(user.id),
            }
        _record_delivery(
            user=user,
            notification=notification,
            channel=NotificationChannel.IN_APP,
            result=deliveries["in_app"],
        )

    if "email" in selected_channels:
        if not email_template:
            deliveries["email"] = {
                "channel": "email",
                "status": "skipped",
                "reason": "template_missing",
                "recipient": user.email,
            }
        elif not user.email:
            deliveries["email"] = {
                "channel": "email",
                "status": "skipped",
                "reason": "recipient_missing",
                "recipient": None,
            }
        elif not _channel_allowed(preferences, "email", is_marketing=is_marketing):
            deliveries["email"] = {
                "channel": "email",
                "status": "skipped",
                "reason": "preference_disabled",
                "recipient": user.email,
            }
        else:
            deliveries["email"] = send_email(
                to_email=user.email,
                subject=email_subject or title,
                template=email_template,
                context={
                    "headline": title,
                    "message": message,
                    "user_name": user.full_name,
                    **(email_context or {}),
                },
            )
        _record_delivery(
            user=user,
            notification=notification,
            channel=NotificationChannel.EMAIL,
            result=deliveries["email"],
        )

    if "sms" in selected_channels:
        if not sms_message:
            sms_result = {
                "channel": "sms",
                "status": "skipped",
                "reason": "message_missing",
                "recipient": user.phone_number,
            }
        elif not user.phone_number:
            sms_result = {
                "channel": "sms",
                "status": "skipped",
                "reason": "recipient_missing",
                "recipient": None,
            }
        elif not _channel_allowed(preferences, "sms", is_marketing=is_marketing):
            sms_result = {
                "channel": "sms",
                "status": "skipped",
                "reason": "preference_disabled",
                "recipient": user.phone_number,
            }
        else:
            sms_result = {
                "channel": "sms",
                "status": "skipped",
                "reason": "sms_paused",
                "recipient": user.phone_number,
                "category": "marketing" if is_marketing else "transactional",
            }
        deliveries["sms"] = sms_result
        _record_delivery(
            user=user,
            notification=notification,
            channel=NotificationChannel.SMS,
            result=sms_result,
        )

    return {"notification": notification, "deliveries": deliveries}


def dispatch_bulk_notification(
    *,
    users: list[User],
    notification_type: NotificationType,
    title: str,
    message: str,
    email_subject: str | None = None,
    email_template: str | None = None,
    email_context: dict | None = None,
    sms_message: str | None = None,
    is_marketing: bool = False,
    channels: set[str] | None = None,
) -> dict:
    selected_channels = set(channels or DEFAULT_CHANNELS)
    batch_limit = current_app.config["BULK_NOTIFICATION_BATCH_SIZE"]
    limited_users = users[:batch_limit]
    results = []
    sms_recipients: list[str] = []
    sms_delivery_users: list[User] = []

    for user in limited_users:
        preferences = get_or_create_notification_preferences(user)
        user_channels = set(selected_channels)
        if "sms" in user_channels and _channel_allowed(preferences, "sms", is_marketing=is_marketing):
            if user.phone_number and sms_message:
                sms_recipients.append(user.phone_number)
                sms_delivery_users.append(user)
            user_channels.discard("sms")

        result = dispatch_user_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            email_subject=email_subject,
            email_template=email_template,
            email_context=email_context,
            sms_message=None,
            is_marketing=is_marketing,
            channels=user_channels,
        )
        results.append({"user_id": user.id, "deliveries": result["deliveries"]})

    bulk_sms_result = None
    if "sms" in selected_channels and sms_message:
        bulk_sms_result = {
            "channel": "sms",
            "mode": "bulk",
            "status": "skipped",
            "reason": "sms_paused",
            "recipient_count": len(sms_recipients),
            "deliveries": [],
        }
        for user in sms_delivery_users:
            sms_delivery = {
                "channel": "sms",
                "mode": "bulk",
                "status": "skipped",
                "reason": "sms_paused",
                "recipient": user.phone_number,
                "category": "marketing" if is_marketing else "transactional",
            }
            _record_delivery(
                user=user,
                notification=None,
                channel=NotificationChannel.SMS,
                result=sms_delivery,
            )

    return {
        "targeted_count": len(limited_users),
        "batch_limit": batch_limit,
        "results": results,
        "bulk_sms": bulk_sms_result,
    }


def retry_notification_delivery(delivery: NotificationDelivery) -> tuple[dict | None, str | None]:
    if delivery.channel != NotificationChannel.EMAIL:
        return None, "Only email deliveries can be retried in the current notification polish slice."
    if not delivery.recipient or not delivery.template or not delivery.subject:
        return None, "The selected email delivery record is missing retry metadata."

    payload_context = {}
    if delivery.notification is not None:
        payload_context = {
            "headline": delivery.notification.title,
            "message": delivery.notification.message,
            "user_name": delivery.notification.user.full_name,
        }
    result = send_email(
        to_email=delivery.recipient,
        subject=delivery.subject,
        template=delivery.template,
        context=payload_context,
    )
    delivery.status = _normalize_delivery_status(result.get("status"))
    delivery.reason = result.get("reason")
    delivery.payload_snapshot = json.dumps(result, sort_keys=True)
    delivery.retry_count += 1
    delivery.last_attempted_at = db.func.now()
    return result, None
