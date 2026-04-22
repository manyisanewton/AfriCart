from flask import current_app


def send_email(*, to_email: str, subject: str, template: str, context: dict | None = None) -> dict:
    queued = current_app.config.get("TASK_QUEUE_ENABLED", False)
    current_app.logger.info(
        "Email dispatch prepared for %s using template %s",
        to_email,
        template,
    )
    return {
        "channel": "email",
        "status": "queued" if queued else "processed",
        "recipient": to_email,
        "subject": subject,
        "template": template,
        "context": context or {},
    }
