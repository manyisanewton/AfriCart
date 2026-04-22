from flask import current_app


def send_sms(*, phone_number: str, message: str) -> dict:
    queued = current_app.config.get("TASK_QUEUE_ENABLED", False)
    current_app.logger.info("SMS dispatch prepared for %s", phone_number)
    return {
        "channel": "sms",
        "status": "queued" if queued else "processed",
        "recipient": phone_number,
        "message": message,
    }
