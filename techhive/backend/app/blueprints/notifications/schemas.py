from app.models import NotificationPreference


PREFERENCE_FIELDS = {
    "in_app_enabled",
    "email_enabled",
    "sms_enabled",
    "transactional_email_enabled",
    "transactional_sms_enabled",
    "marketing_email_enabled",
    "marketing_sms_enabled",
}


def validate_notification_preferences_payload(payload: dict | None) -> dict:
    data = payload or {}
    provided_fields = {field for field in PREFERENCE_FIELDS if field in data}
    if not provided_fields:
        return {"errors": {"preferences": "At least one preference field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    for field in provided_fields:
        normalized[field] = bool(data.get(field))
    return normalized


def serialize_notification_preferences(preferences: NotificationPreference) -> dict:
    return {
        "in_app_enabled": preferences.in_app_enabled,
        "email_enabled": preferences.email_enabled,
        "sms_enabled": preferences.sms_enabled,
        "transactional_email_enabled": preferences.transactional_email_enabled,
        "transactional_sms_enabled": preferences.transactional_sms_enabled,
        "marketing_email_enabled": preferences.marketing_email_enabled,
        "marketing_sms_enabled": preferences.marketing_sms_enabled,
        "updated_at": preferences.updated_at.isoformat(),
    }


def serialize_notification_delivery(delivery) -> dict:
    return {
        "id": delivery.id,
        "notification_id": delivery.notification_id,
        "channel": delivery.channel.value,
        "status": delivery.status.value,
        "recipient": delivery.recipient,
        "subject": delivery.subject,
        "template": delivery.template,
        "category": delivery.category,
        "reason": delivery.reason,
        "retry_count": delivery.retry_count,
        "last_attempted_at": delivery.last_attempted_at.isoformat()
        if delivery.last_attempted_at
        else None,
        "created_at": delivery.created_at.isoformat(),
        "updated_at": delivery.updated_at.isoformat(),
    }
