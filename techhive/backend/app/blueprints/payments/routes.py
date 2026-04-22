from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.notifications.push import create_notification
from app.blueprints.payments import payments_bp
from app.blueprints.payments.helpers import generate_payment_reference, serialize_payment
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import NotificationType, Order, OrderStatus, Payment, PaymentMethod, PaymentStatus


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

    try:
        order_id = int(order_id)
        if order_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return validation_error({"order_id": "order_id must be a positive integer."})

    allowed_methods = {member.value for member in PaymentMethod}
    if method not in allowed_methods:
        return validation_error({"method": "Unsupported payment method."})

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
    db.session.add(payment)
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
