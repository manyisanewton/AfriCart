from datetime import datetime

from app.models import Payment


def generate_payment_reference() -> str:
    return f"PAY-{datetime.utcnow():%Y%m%d%H%M%S%f}"


def serialize_payment(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "reference": payment.reference,
        "method": payment.method.value,
        "status": payment.status.value,
        "amount": payment.amount_value,
        "currency": payment.currency,
        "provider_response": payment.provider_response,
        "created_at": payment.created_at.isoformat(),
    }
