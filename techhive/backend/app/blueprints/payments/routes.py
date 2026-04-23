from datetime import datetime, timezone

from flask import current_app, g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.notifications.push import create_notification
from app.blueprints.payments import payments_bp
from app.blueprints.payments.helpers import (
    dump_provider_response,
    generate_payment_reference,
    serialize_payment,
)
from app.blueprints.payments.mpesa import MpesaConfigurationError, MpesaGatewayError
from app.blueprints.payments.webhooks import (
    apply_provider_webhook,
    initiate_provider_payment,
    is_daraja_callback_payload,
    should_accept_unsigned_mpesa_callback,
    verify_provider_webhook,
)
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import NotificationType, Order, OrderStatus, Payment, PaymentMethod, PaymentStatus
from app.services.payment_reconciliation_service import build_payment_reconciliation_deadline


def _load_user_order(order_id: int, user_id: int):
    return Order.query.filter_by(id=order_id, user_id=user_id).first()


def _payment_not_found():
    return jsonify({"error": {"code": "not_found", "message": "Payment not found."}}), 404


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
    payload = request.get_json(silent=True) or {}
    order_id = payload.get("order_id")
    method = str(payload.get("method", PaymentMethod.MANUAL.value)).strip().lower()
    phone_number = str(payload.get("phone_number") or "").strip() or None

    try:
        order_id = int(order_id)
        if order_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return validation_error({"order_id": "order_id must be a positive integer."})

    allowed_methods = {member.value for member in PaymentMethod}
    if method not in allowed_methods:
        return validation_error({"method": "Unsupported payment method."})

    if method == PaymentMethod.MPESA.value and not phone_number:
        return validation_error({"phone_number": "phone_number is required for mpesa payments."})

    order = _load_user_order(order_id, g.current_user.id)
    if order is None:
        return validation_error({"order_id": "Order was not found."})

    existing = Payment.query.filter_by(order_id=order.id, status=PaymentStatus.PENDING).first()
    if existing is not None:
        return jsonify({"item": serialize_payment(existing)}), 200

    payment = Payment(
        order_id=order.id,
        reference=generate_payment_reference(),
        method=PaymentMethod(method),
        status=PaymentStatus.PENDING,
        amount=order.total_amount,
        currency=order.currency,
    )
    if payment.method == PaymentMethod.MPESA:
        payment.initiated_at = datetime.now(timezone.utc)
        payment.reconciliation_due_at = build_payment_reconciliation_deadline(
            current_app.config["MPESA_RECONCILIATION_TIMEOUT_MINUTES"]
        )
    db.session.add(payment)
    db.session.flush()

    try:
        provider_payload = initiate_provider_payment(
            payment,
            callback_base_url=current_app.config["PAYMENT_CALLBACK_BASE_URL"],
            payload={"phone_number": phone_number},
        )
    except MpesaConfigurationError as exc:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": {
                        "code": "payment_configuration_error",
                        "message": str(exc),
                    }
                }
            ),
            503,
        )
    except MpesaGatewayError as exc:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = "provider_request_failed"
        payment.failure_message = str(exc)
        payment.processed_at = datetime.now(timezone.utc)
        payment.reconciliation_due_at = None
        payment.provider_response = dump_provider_response(
            {
                "provider": payment.method.value,
                "failure_code": payment.failure_code,
                "failure_message": payment.failure_message,
            }
        )
        db.session.commit()
        return (
            jsonify(
                {
                    "error": {
                        "code": "payment_provider_unavailable",
                        "message": str(exc),
                    }
                }
            ),
            502,
        )

    payment.external_reference = (
        provider_payload.get("checkout_request_id")
        or provider_payload.get("payment_intent_id")
        or provider_payload.get("tx_ref")
        or provider_payload.get("order_id")
    )
    payment.provider_event_id = provider_payload.get("merchant_request_id") or payment.provider_event_id
    payment.payer_phone_number = provider_payload.get("phone_number")
    payment.redirect_url = provider_payload.get("redirect_url")
    payment.provider_response = dump_provider_response(provider_payload)
    create_notification(
        g.current_user.id,
        NotificationType.PAYMENT_CREATED,
        "Payment created",
        f"Payment {payment.reference} has been created for order {order.order_number}.",
    )
    db.session.commit()
    return jsonify({"item": serialize_payment(payment)}), 201


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
    payment = (
        Payment.query.join(Order)
        .filter(Payment.id == payment_id, Order.user_id == g.current_user.id)
        .first()
    )
    if payment is None:
        return _payment_not_found()

    payment.status = PaymentStatus.PAID
    payment.order.status = OrderStatus.CONFIRMED
    payment.provider_response = "Payment marked as paid in local development flow."
    create_notification(
        g.current_user.id,
        NotificationType.PAYMENT_PAID,
        "Payment successful",
        f"Payment {payment.reference} was marked as paid.",
    )
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
    payment = (
        Payment.query.join(Order)
        .filter(Payment.id == payment_id, Order.user_id == g.current_user.id)
        .first()
    )
    if payment is None:
        return _payment_not_found()

    payment.status = PaymentStatus.FAILED
    payment.provider_response = "Payment marked as failed in local development flow."
    create_notification(
        g.current_user.id,
        NotificationType.PAYMENT_FAILED,
        "Payment failed",
        f"Payment {payment.reference} was marked as failed.",
    )
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
    payload = request.get_json(silent=True) or {}

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
