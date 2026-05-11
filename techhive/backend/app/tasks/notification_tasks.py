from app.services.email_service import send_email
from app.services.sms_service import send_bulk_sms, send_sms


def send_payment_status_sms(*, phone_number: str, order_number: str, status: str) -> dict:
    return send_sms(
        phone_number=phone_number,
        message=f"Your TechHive order {order_number} payment status is {status}.",
    )


def send_notification_email(
    *,
    to_email: str,
    subject: str,
    template: str,
    context: dict | None = None,
) -> dict:
    return send_email(
        to_email=to_email,
        subject=subject,
        template=template,
        context=context,
    )


def send_bulk_notification_email(
    *,
    recipients: list[dict],
    subject: str,
    template: str,
) -> list[dict]:
    results = []
    for recipient in recipients:
        results.append(
            send_email(
                to_email=recipient["to_email"],
                subject=subject,
                template=template,
                context=recipient.get("context"),
            )
        )
    return results


def send_bulk_notification_sms(*, phone_numbers: list[str], message: str) -> dict:
    return send_bulk_sms(phone_numbers=phone_numbers, message=message, category="marketing")
