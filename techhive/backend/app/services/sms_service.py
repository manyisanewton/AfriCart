from __future__ import annotations

from base64 import b64encode
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


def _twilio_is_configured() -> bool:
    return bool(
        current_app.config.get("TWILIO_ACCOUNT_SID")
        and current_app.config.get("TWILIO_AUTH_TOKEN")
        and (
            current_app.config.get("TWILIO_FROM_NUMBER")
            or current_app.config.get("TWILIO_MESSAGING_SERVICE_SID")
        )
    )


def normalize_phone_number(phone_number: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone_number or "")
    if cleaned.startswith("+"):
        return "+" + re.sub(r"\D", "", cleaned[1:])
    digits = re.sub(r"\D", "", cleaned)
    if digits.startswith("0") and len(digits) == 10:
        return f"+254{digits[1:]}"
    if digits.startswith("254") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}" if digits else phone_number


def send_sms(*, phone_number: str, message: str, category: str = "transactional") -> dict:
    normalized_phone_number = normalize_phone_number(phone_number)
    queued = current_app.config.get("TASK_QUEUE_ENABLED", False)
    delivery = {
        "channel": "sms",
        "recipient": normalized_phone_number,
        "category": category,
        "message": message,
    }

    if queued:
        current_app.logger.info("SMS queued for %s", normalized_phone_number)
        return {**delivery, "status": "queued"}

    if not _twilio_is_configured():
        current_app.logger.info("SMS prepared for %s", normalized_phone_number)
        return {
            **delivery,
            "status": "prepared",
            "provider": "twilio",
            "reason": "twilio_not_configured",
        }

    account_sid = current_app.config["TWILIO_ACCOUNT_SID"]
    auth_token = current_app.config["TWILIO_AUTH_TOKEN"]
    payload = {"To": normalized_phone_number, "Body": message}
    if current_app.config.get("TWILIO_MESSAGING_SERVICE_SID"):
        payload["MessagingServiceSid"] = current_app.config["TWILIO_MESSAGING_SERVICE_SID"]
    else:
        payload["From"] = normalize_phone_number(current_app.config["TWILIO_FROM_NUMBER"])

    encoded = urlencode(payload).encode("utf-8")
    token = b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("utf-8")
    request = Request(
        (
            f"{current_app.config['TWILIO_API_BASE_URL'].rstrip('/')}"
            f"/2010-04-01/Accounts/{account_sid}/Messages.json"
        ),
        data=encoded,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            status_code = response.getcode()
    except OSError as exc:
        current_app.logger.warning("Twilio delivery failed for %s: %s", normalized_phone_number, exc)
        return {
            **delivery,
            "status": "failed",
            "provider": "twilio",
            "reason": str(exc),
        }

    current_app.logger.info("SMS sent to %s", normalized_phone_number)
    return {
        **delivery,
        "status": "sent" if 200 <= status_code < 300 else "failed",
        "provider": "twilio",
    }


def send_bulk_sms(*, phone_numbers: list[str], message: str, category: str = "transactional") -> dict:
    recipients = [phone for phone in dict.fromkeys(phone_numbers) if phone]
    deliveries = [
        send_sms(phone_number=phone_number, message=message, category=category)
        for phone_number in recipients
    ]
    return {
        "channel": "sms",
        "mode": "bulk",
        "recipient_count": len(recipients),
        "deliveries": deliveries,
    }
