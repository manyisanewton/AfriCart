from flask import current_app, g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.payments import payments_bp
from app.blueprints.payments.helpers import serialize_payment
from app.blueprints.payments.webhooks import (
    apply_provider_webhook,
    is_daraja_callback_payload,
    should_accept_unsigned_mpesa_callback,
    verify_provider_webhook,
)
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import Order, Payment, PaymentMethod
from app.services.payment_service import (
    apply_failed_state,
    apply_paid_state,
    create_payment_for_order,
    get_user_payment,
)
from app.utils.api import get_json_payload, not_found_response


@payments_bp.post("")
@auth_required
def create_payment():
    """
    Create a payment record for an authenticated user's order.
    ---
    tags:
      - Payments
    responses:
      201:
        description: Payment created.
    """
    payload = get_json_payload()
    method = str(payload.get("method", PaymentMethod.MANUAL.value)).strip().lower()
    phone_number = str(payload.get("phone_number") or "").strip() or None
    payment, error, status_code = create_payment_for_order(
        user_id=g.current_user.id,
        order_id=payload.get("order_id"),
        method=method,
        phone_number=phone_number,
        callback_base_url=current_app.config["PAYMENT_CALLBACK_BASE_URL"],
        reconciliation_timeout_minutes=current_app.config["MPESA_RECONCILIATION_TIMEOUT_MINUTES"],
    )
    if error:
        if error.code == "validation_error":
            return validation_error(error.details or {"payment": error.message})
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status_code

    db.session.commit()
    return jsonify({"item": serialize_payment(payment)}), status_code


@payments_bp.get("")
@auth_required
def list_payments():
    """
    List authenticated user's payments.
    ---
    tags:
      - Payments
    responses:
      200:
        description: Payments list.
    """
    payments = (
        Payment.query.join(Order)
        .filter(Order.user_id == g.current_user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_payment(payment) for payment in payments]})


@payments_bp.post("/<int:payment_id>/mark-paid")
@auth_required
def mark_payment_paid(payment_id: int):
    """
    Mark a payment as paid for testing and internal flow validation.
    ---
    tags:
      - Payments
    responses:
      200:
        description: Payment marked as paid.
    """
    payment = get_user_payment(user_id=g.current_user.id, payment_id=payment_id)
    if payment is None:
        return not_found_response("Payment not found.")

    try:
        apply_paid_state(
            payment,
            user_id=g.current_user.id,
            provider_response="Payment marked as paid in local development flow.",
            notification_message=f"Payment {payment.reference} was marked as paid.",
        )
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_payment_transition", "message": str(exc)}}), 400
    db.session.commit()
    return jsonify({"item": serialize_payment(payment)})


@payments_bp.post("/<int:payment_id>/mark-failed")
@auth_required
def mark_payment_failed(payment_id: int):
    """
    Mark a payment as failed for testing and internal flow validation.
    ---
    tags:
      - Payments
    responses:
      200:
        description: Payment marked as failed.
    """
    payment = get_user_payment(user_id=g.current_user.id, payment_id=payment_id)
    if payment is None:
        return not_found_response("Payment not found.")

    try:
        apply_failed_state(
            payment,
            user_id=g.current_user.id,
            provider_response="Payment marked as failed in local development flow.",
            notification_message=f"Payment {payment.reference} was marked as failed.",
        )
    except ValueError as exc:
        return jsonify({"error": {"code": "invalid_payment_transition", "message": str(exc)}}), 400
    db.session.commit()
    return jsonify({"item": serialize_payment(payment)})


@payments_bp.post("/webhooks/<string:provider>")
def handle_payment_webhook(provider: str):
    """
    Process signed provider webhooks.
    ---
    tags:
      - Payments
    responses:
      200:
        description: Webhook processed.
      401:
        description: Invalid signature.
    """
    provider = provider.strip().lower()
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get("X-TechHive-Signature")
    event_id = request.headers.get("X-TechHive-Event-Id")
    payload = get_json_payload()

    unsigned_daraja_callback = (
        provider == PaymentMethod.MPESA.value
        and not signature
        and should_accept_unsigned_mpesa_callback(payload)
    )

    if not unsigned_daraja_callback and not verify_provider_webhook(provider, raw_body, signature):
        return jsonify({"error": {"code": "invalid_signature", "message": "Webhook signature is invalid."}}), 401

    payment, outcome = apply_provider_webhook(provider, event_id, payload)
    if payment is None:
        error_map = {
            "payment_not_found": (404, "Payment not found."),
            "invalid_order_state": (409, "Payment cannot be applied to the current order state."),
            "amount_mismatch": (409, "Webhook amount does not match the payment."),
            "phone_mismatch": (409, "Webhook phone number does not match the initiated payment."),
            "duplicate_receipt": (409, "Webhook receipt was already used by another payment."),
            "invalid_mpesa_metadata": (400, "M-Pesa callback metadata is incomplete."),
        }
        status_code, message = error_map.get(outcome, (400, "Webhook payload could not be processed."))
        return jsonify({"error": {"code": outcome, "message": message}}), status_code

    db.session.commit()
    if unsigned_daraja_callback or is_daraja_callback_payload(payload):
        return jsonify(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted",
                "item": serialize_payment(payment),
                "result": outcome,
            }
        )
    return jsonify({"item": serialize_payment(payment), "result": outcome})
