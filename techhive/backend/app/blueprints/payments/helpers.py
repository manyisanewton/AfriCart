from datetime import datetime, timezone
import hashlib
import hmac
import json

from app.models import Payment


def generate_payment_reference() -> str:
    return f"PAY-{datetime.now(timezone.utc):%Y%m%d%H%M%S%f}"


def sign_webhook_payload(secret: str, raw_body: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, raw_body: str, signature: str | None) -> bool:
    if not signature:
        return False
    expected = sign_webhook_payload(secret, raw_body)
    return hmac.compare_digest(expected, signature)


def dump_provider_response(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, sort_keys=True)


def serialize_payment(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "reference": payment.reference,
        "method": payment.method.value,
        "status": payment.status.value,
        "amount": payment.amount_value,
        "currency": payment.currency,
        "external_reference": payment.external_reference,
        "provider_event_id": payment.provider_event_id,
        "payer_phone_number": payment.payer_phone_number,
        "provider_receipt": payment.provider_receipt,
        "redirect_url": payment.redirect_url,
        "initiated_at": payment.initiated_at.isoformat() if payment.initiated_at else None,
        "reconciliation_due_at": (
            payment.reconciliation_due_at.isoformat() if payment.reconciliation_due_at else None
        ),
        "reconciliation_attempts": payment.reconciliation_attempts,
        "failure_code": payment.failure_code,
        "failure_message": payment.failure_message,
        "provider_response": payment.provider_response,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
        "created_at": payment.created_at.isoformat(),
    }
