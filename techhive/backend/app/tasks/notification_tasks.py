from app.services.sms_service import send_sms


def send_payment_status_sms(*, phone_number: str, order_number: str, status: str) -> dict:
    return send_sms(
        phone_number=phone_number,
        message=f"Your TechHive order {order_number} payment status is {status}.",
    )
