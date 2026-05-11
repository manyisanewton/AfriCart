from __future__ import annotations

import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import unescape

from flask import current_app, render_template
from jinja2 import TemplateNotFound


def _html_to_text(html: str) -> str:
    compact = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
    compact = re.sub(r"</p\s*>", "\n\n", compact, flags=re.IGNORECASE)
    compact = re.sub(r"<[^>]+>", "", compact)
    return re.sub(r"\n{3,}", "\n\n", unescape(compact)).strip()


def render_email_template(template: str, context: dict | None = None) -> dict[str, str]:
    template_context = {
        "app_name": current_app.config["APP_NAME"],
        "support_email": current_app.config.get("SMTP_REPLY_TO")
        or current_app.config.get("SMTP_FROM_EMAIL"),
        "year": datetime.now().year,
        **(context or {}),
    }
    html = render_template(f"emails/{template}.html", **template_context)
    try:
        text = render_template(f"emails/{template}.txt", **template_context)
    except TemplateNotFound:
        text = _html_to_text(html)
    return {"html": html, "text": text}


def _smtp_is_configured() -> bool:
    return bool(
        current_app.config.get("SMTP_HOST")
        and current_app.config.get("SMTP_FROM_EMAIL")
    )


def send_email(*, to_email: str, subject: str, template: str, context: dict | None = None) -> dict:
    rendered = render_email_template(template, context)
    queued = current_app.config.get("TASK_QUEUE_ENABLED", False)
    delivery = {
        "channel": "email",
        "recipient": to_email,
        "subject": subject,
        "template": template,
    }

    if queued:
        current_app.logger.info("Email queued for %s using template %s", to_email, template)
        return {**delivery, "status": "queued"}

    if not _smtp_is_configured():
        current_app.logger.info("Email prepared for %s using template %s", to_email, template)
        return {
            **delivery,
            "status": "prepared",
            "provider": "smtp",
            "reason": "smtp_not_configured",
        }

    message = EmailMessage()
    from_name = current_app.config.get("SMTP_FROM_NAME") or current_app.config["APP_NAME"]
    from_email = current_app.config["SMTP_FROM_EMAIL"]
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    reply_to = current_app.config.get("SMTP_REPLY_TO")
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(rendered["text"])
    message.add_alternative(rendered["html"], subtype="html")

    try:
        smtp_class = smtplib.SMTP_SSL if current_app.config.get("SMTP_USE_SSL") else smtplib.SMTP
        with smtp_class(
            current_app.config["SMTP_HOST"],
            current_app.config["SMTP_PORT"],
            timeout=current_app.config["SMTP_TIMEOUT_SECONDS"],
        ) as smtp_client:
            if not current_app.config.get("SMTP_USE_SSL") and current_app.config.get("SMTP_USE_TLS"):
                smtp_client.starttls()
            if current_app.config.get("SMTP_USERNAME"):
                smtp_client.login(
                    current_app.config["SMTP_USERNAME"],
                    current_app.config.get("SMTP_PASSWORD") or "",
                )
            smtp_client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        current_app.logger.warning("SMTP delivery failed for %s: %s", to_email, exc)
        return {
            **delivery,
            "status": "failed",
            "provider": "smtp",
            "reason": str(exc),
        }

    current_app.logger.info("Email sent to %s using template %s", to_email, template)
    return {
        **delivery,
        "status": "sent",
        "provider": "smtp",
    }
