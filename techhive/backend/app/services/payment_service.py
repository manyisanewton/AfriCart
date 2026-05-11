from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from flask import current_app

from app.blueprints.payments.helpers import dump_provider_response, generate_payment_reference
from app.blueprints.payments.mpesa import (
    MpesaConfigurationError,
    MpesaGatewayError,
    MpesaValidationError,
    normalize_mpesa_phone_number,
    validate_mpesa_configuration,
)
from app.services.commerce_state_service import transition_order, transition_payment
from app.extensions import db
from app.models import NotificationType, Order, OrderStatus, Payment, PaymentMethod, PaymentStatus
from app.services.notification_dispatch_service import dispatch_user_notification
from app.services.payment_reconciliation_service import build_payment_reconciliation_deadline
from app.utils.helpers import format_money


@dataclass
class ServiceError:
    code: str
    message: str
    status_code: int
    details: dict[str, str] | None = None


def get_user_order(*, user_id: int, order_id: int) -> Order | None:
    return Order.query.filter_by(id=order_id, user_id=user_id).first()


def get_user_payment(*, user_id: int, payment_id: int) -> Payment | None:
    return (
        Payment.query.join(Order)
        .filter(Payment.id == payment_id, Order.user_id == user_id)
        .first()
    )


def apply_paid_state(
    payment: Payment,
    *,
    user_id: int,
    provider_response: str,
    notification_message: str,
) -> Payment:
    payment_error = transition_payment(payment, PaymentStatus.PAID)
    if payment_error is not None:
        raise ValueError(payment_error.message)
    order_error = transition_order(payment.order, OrderStatus.CONFIRMED)
    if order_error is not None:
        raise ValueError(order_error.message)
    payment.provider_response = provider_response
    payment.failure_code = None
    payment.failure_message = None
    payment.processed_at = datetime.now(timezone.utc)
    dispatch_user_notification(
        user=payment.order.user,
        notification_type=NotificationType.PAYMENT_PAID,
        title="Payment successful",
        message=notification_message,
        email_subject=f"Payment received for order {payment.order.order_number}",
        email_template="payment_status",
        email_context={
            "order_number": payment.order.order_number,
            "payment_reference": payment.reference,
            "amount": format_money(payment.amount),
            "status_label": "Paid",
            "status_tone": "success",
            "headline": "Your payment has been confirmed",
        },
        sms_message=f"TechHive: payment for order {payment.order.order_number} was confirmed.",
    )
    return payment


def apply_failed_state(
    payment: Payment,
    *,
    user_id: int,
    provider_response: str,
    notification_message: str,
    failure_code: str | None = None,
    failure_message: str | None = None,
) -> Payment:
    payment_error = transition_payment(payment, PaymentStatus.FAILED)
    if payment_error is not None:
        raise ValueError(payment_error.message)
    payment.provider_response = provider_response
    payment.failure_code = failure_code
    payment.failure_message = failure_message
    payment.processed_at = datetime.now(timezone.utc)
    payment.reconciliation_due_at = None
    dispatch_user_notification(
        user=payment.order.user,
        notification_type=NotificationType.PAYMENT_FAILED,
        title="Payment failed",
        message=notification_message,
        email_subject=f"Payment failed for order {payment.order.order_number}",
        email_template="payment_status",
        email_context={
            "order_number": payment.order.order_number,
            "payment_reference": payment.reference,
            "amount": format_money(payment.amount),
            "status_label": "Failed",
            "status_tone": "attention",
            "headline": "Your payment did not go through",
            "failure_message": failure_message,
        },
        sms_message=f"TechHive: payment for order {payment.order.order_number} failed.",
    )
    return payment


def create_payment_for_order(
    *,
    user_id: int,
    order_id: int,
    method: str,
    phone_number: str | None,
    callback_base_url: str,
    reconciliation_timeout_minutes: int,
) -> tuple[Payment | None, ServiceError | None, int]:
    try:
        order_id = int(order_id)
        if order_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return (
            None,
            ServiceError(
                "validation_error",
                "order_id must be a positive integer.",
                400,
                {"order_id": "order_id must be a positive integer."},
            ),
            400,
        )

    allowed_methods = {member.value for member in PaymentMethod}
    enabled_methods = {
        str(value).strip().lower()
        for value in current_app.config.get("PAYMENT_ENABLED_METHODS", ())
        if str(value).strip()
    }
    if method not in allowed_methods:
        return (
            None,
            ServiceError(
                "validation_error",
                "Unsupported payment method.",
                400,
                {"method": "Unsupported payment method."},
            ),
            400,
        )
    if enabled_methods and method not in enabled_methods:
        return (
            None,
            ServiceError(
                "validation_error",
                "This payment method is currently unavailable.",
                400,
                {"method": "This payment method is currently unavailable."},
            ),
            400,
        )

    if method == PaymentMethod.MPESA.value and not phone_number:
        return (
            None,
            ServiceError(
                "validation_error",
                "phone_number is required for mpesa payments.",
                400,
                {"phone_number": "phone_number is required for mpesa payments."},
            ),
            400,
        )
    if method == PaymentMethod.MPESA.value:
        try:
            validate_mpesa_configuration(callback_base_url)
            normalize_mpesa_phone_number(phone_number)
        except MpesaValidationError as exc:
            return (
                None,
                ServiceError(
                    "validation_error",
                    str(exc),
                    400,
                    {"phone_number": str(exc)},
                ),
                400,
            )
        except MpesaConfigurationError as exc:
            return (
                None,
                ServiceError("payment_configuration_error", str(exc), 503),
                503,
            )

    order = get_user_order(user_id=user_id, order_id=order_id)
    if order is None:
        return (
            None,
            ServiceError(
                "validation_error",
                "Order was not found.",
                400,
                {"order_id": "Order was not found."},
            ),
            400,
        )

    existing = Payment.query.filter_by(order_id=order.id, status=PaymentStatus.PENDING).first()
    if existing is not None:
        return existing, None, 200

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
            reconciliation_timeout_minutes
        )
    db.session.add(payment)
    db.session.commit()

    try:
        from app.blueprints.payments.webhooks import initiate_provider_payment

        provider_payload = initiate_provider_payment(
            payment,
            callback_base_url=callback_base_url,
            payload={"phone_number": phone_number},
        )
    except MpesaValidationError as exc:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = "validation_error"
        payment.failure_message = str(exc)
        payment.processed_at = datetime.now(timezone.utc)
        payment.reconciliation_due_at = None
        db.session.commit()
        return (None, ServiceError("validation_error", str(exc), 400, {"phone_number": str(exc)}), 400)
    except MpesaConfigurationError as exc:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = "payment_configuration_error"
        payment.failure_message = str(exc)
        payment.processed_at = datetime.now(timezone.utc)
        payment.reconciliation_due_at = None
        db.session.commit()
        return (
            None,
            ServiceError("payment_configuration_error", str(exc), 503),
            503,
        )
    except MpesaGatewayError as exc:
        apply_failed_state(
            payment,
            user_id=user_id,
            provider_response=dump_provider_response(
                {
                    "provider": payment.method.value,
                    "failure_code": "provider_request_failed",
                    "failure_message": str(exc),
                }
            ),
            notification_message=f"Payment {payment.reference} could not be initiated.",
            failure_code="provider_request_failed",
            failure_message=str(exc),
        )
        db.session.commit()
        return (
            None,
            ServiceError("payment_provider_unavailable", str(exc), 502),
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
    db.session.commit()
    dispatch_user_notification(
        user=order.user,
        notification_type=NotificationType.PAYMENT_CREATED,
        title="Payment created",
        message=f"Payment {payment.reference} has been created for order {order.order_number}.",
        email_subject=f"Payment started for order {order.order_number}",
        email_template="payment_status",
        email_context={
            "order_number": order.order_number,
            "payment_reference": payment.reference,
            "amount": format_money(payment.amount),
            "status_label": "Pending",
            "status_tone": "info",
            "headline": "Your payment request is ready",
        },
        sms_message=f"TechHive: payment request for order {order.order_number} has been created.",
    )
    return payment, None, 201
