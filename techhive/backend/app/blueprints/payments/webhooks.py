from datetime import datetime, timezone

from flask import current_app

from app.blueprints.notifications.push import create_notification
from app.blueprints.payments.flutterwave import create_flutterwave_payment
from app.blueprints.payments.helpers import dump_provider_response, verify_webhook_signature
from app.blueprints.payments.mpesa import classify_mpesa_result_code, initiate_mpesa_payment
from app.blueprints.payments.paypal import create_paypal_order
from app.blueprints.payments.stripe_gateway import create_stripe_payment_intent
from app.models import NotificationType, OrderStatus, Payment, PaymentMethod, PaymentStatus
from app.services.payment_service import apply_failed_state, apply_paid_state


PROVIDER_SECRETS = {
    PaymentMethod.MPESA.value: "MPESA_WEBHOOK_SECRET",
    PaymentMethod.STRIPE.value: "STRIPE_WEBHOOK_SECRET",
    PaymentMethod.FLUTTERWAVE.value: "FLUTTERWAVE_WEBHOOK_SECRET",
    PaymentMethod.PAYPAL.value: "PAYPAL_WEBHOOK_SECRET",
}


def initiate_provider_payment(payment: Payment, *, callback_base_url: str, payload: dict) -> dict:
    if payment.method == PaymentMethod.MPESA:
        return initiate_mpesa_payment(payment, callback_base_url, payload["phone_number"])
    if payment.method == PaymentMethod.STRIPE:
        return create_stripe_payment_intent(payment, callback_base_url)
    if payment.method == PaymentMethod.FLUTTERWAVE:
        return create_flutterwave_payment(payment, callback_base_url)
    if payment.method == PaymentMethod.PAYPAL:
        return create_paypal_order(payment, callback_base_url)
    return {"provider": payment.method.value}


def verify_provider_webhook(provider: str, raw_body: str, signature: str | None) -> bool:
    config_key = PROVIDER_SECRETS.get(provider)
    if config_key is None:
        return False
    secret = current_app.config.get(config_key)
    return verify_webhook_signature(secret, raw_body, signature)


def is_daraja_callback_payload(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    callback = payload.get("Body", {}).get("stkCallback", {})
    if not isinstance(callback, dict):
        return False
    required_keys = {"MerchantRequestID", "CheckoutRequestID", "ResultCode"}
    return required_keys.issubset(callback.keys())


def should_accept_unsigned_mpesa_callback(payload: dict | None) -> bool:
    return current_app.config.get("MPESA_ALLOW_UNSIGNED_CALLBACKS", False) and is_daraja_callback_payload(payload)


def apply_provider_webhook(provider: str, event_id: str | None, payload: dict) -> tuple[Payment | None, str]:
    normalized = normalize_provider_webhook(provider, payload, event_id)
    if normalized.get("error_code"):
        return None, normalized["error_code"]

    payment = None
    if normalized["external_reference"]:
        payment = Payment.query.filter_by(external_reference=normalized["external_reference"]).first()
    if payment is None and normalized["reference"]:
        payment = Payment.query.filter_by(reference=normalized["reference"]).first()

    if payment is None or payment.method.value != provider:
        return None, "payment_not_found"

    if normalized["event_id"] and payment.provider_event_id == normalized["event_id"]:
        return payment, "duplicate"

    if payment.status == PaymentStatus.PAID and normalized["status"] == PaymentStatus.PAID.value:
        return payment, "already_processed"

    provider_receipt = normalized.get("provider_receipt")
    if provider_receipt:
        existing_receipt = Payment.query.filter_by(provider_receipt=provider_receipt).first()
        if existing_receipt is not None and existing_receipt.id != payment.id:
            return None, "duplicate_receipt"

    if (
        normalized["status"] == PaymentStatus.PAID.value
        and payment.order.status == OrderStatus.CANCELLED
    ):
        return None, "invalid_order_state"

    if normalized["status"] == PaymentStatus.PAID.value:
        amount = normalized.get("amount")
        if amount is None or int(float(payment.amount)) != int(float(amount)):
            return None, "amount_mismatch"

        phone_number = normalized.get("phone_number")
        if payment.payer_phone_number and phone_number and payment.payer_phone_number != phone_number:
            return None, "phone_mismatch"

    if normalized["status"] == PaymentStatus.PAID.value:
        payment.provider_receipt = normalized.get("provider_receipt") or payment.provider_receipt
        apply_paid_state(
            payment,
            user_id=payment.order.user_id,
            provider_response=dump_provider_response(normalized["raw"]),
            notification_message=f"Payment {payment.reference} was confirmed by {provider}.",
        )
    elif normalized["status"] == PaymentStatus.FAILED.value:
        apply_failed_state(
            payment,
            user_id=payment.order.user_id,
            provider_response=dump_provider_response(normalized["raw"]),
            notification_message=f"Payment {payment.reference} failed with {provider}.",
            failure_code=normalized.get("failure_code"),
            failure_message=normalized.get("failure_message"),
        )

    payment.provider_event_id = normalized["event_id"] or payment.provider_event_id
    payment.provider_response = dump_provider_response(normalized["raw"])
    return payment, "updated"


def normalize_provider_webhook(provider: str, payload: dict, event_id: str | None) -> dict:
    if provider == PaymentMethod.MPESA.value:
        callback = payload.get("Body", {}).get("stkCallback", {})
        if callback:
            result_code = int(callback.get("ResultCode", 1))
            result_desc = str(callback.get("ResultDesc") or "").strip() or None
            metadata_items = callback.get("CallbackMetadata", {}).get("Item", []) or []
            metadata = {
                item.get("Name"): item.get("Value")
                for item in metadata_items
                if isinstance(item, dict) and item.get("Name")
            }
            if result_code == 0:
                required_fields = ("Amount", "PhoneNumber", "MpesaReceiptNumber")
                missing_fields = [field for field in required_fields if metadata.get(field) in (None, "")]
                if missing_fields:
                    return {
                        "error_code": "invalid_mpesa_metadata",
                        "raw": {
                            "provider": provider,
                            "result_code": result_code,
                            "result_desc": result_desc,
                            "missing_fields": missing_fields,
                        },
                    }

            failure_code, failure_message = classify_mpesa_result_code(result_code, result_desc)
            return {
                "reference": None,
                "external_reference": str(callback.get("CheckoutRequestID") or "").strip() or None,
                "status": PaymentStatus.PAID.value if result_code == 0 else PaymentStatus.FAILED.value,
                "event_id": event_id or str(callback.get("MerchantRequestID") or "").strip() or None,
                "amount": metadata.get("Amount"),
                "phone_number": (
                    str(metadata.get("PhoneNumber")).strip()
                    if metadata.get("PhoneNumber") is not None
                    else None
                ),
                "provider_receipt": (
                    str(metadata.get("MpesaReceiptNumber")).strip()
                    if metadata.get("MpesaReceiptNumber") is not None
                    else None
                ),
                "failure_code": None if result_code == 0 else failure_code,
                "failure_message": None if result_code == 0 else failure_message,
                "raw": {
                    "provider": provider,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "checkout_request_id": callback.get("CheckoutRequestID"),
                    "merchant_request_id": callback.get("MerchantRequestID"),
                    "metadata": metadata,
                },
            }

    return {
        "reference": str(payload.get("reference") or "").strip() or None,
        "external_reference": str(payload.get("external_reference") or "").strip() or None,
        "status": str(payload.get("status") or "").strip().lower(),
        "event_id": event_id,
        "amount": payload.get("amount"),
        "phone_number": str(payload.get("phone_number") or "").strip() or None,
        "provider_receipt": str(payload.get("provider_receipt") or "").strip() or None,
        "raw": payload,
    }
