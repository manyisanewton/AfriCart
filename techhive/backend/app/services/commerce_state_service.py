from __future__ import annotations

from dataclasses import dataclass

from app.models import Order, OrderStatus, Payment, PaymentStatus


@dataclass
class TransitionError:
    code: str
    message: str


ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


ALLOWED_PAYMENT_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.PAID, PaymentStatus.FAILED},
    PaymentStatus.PAID: set(),
    PaymentStatus.FAILED: set(),
}


def transition_order(order: Order, target_status: OrderStatus) -> TransitionError | None:
    if order.status == target_status:
        return None

    allowed = ALLOWED_ORDER_TRANSITIONS.get(order.status, set())
    if target_status not in allowed:
        return TransitionError(
            "invalid_order_transition",
            f"Order cannot transition from {order.status.value} to {target_status.value}.",
        )

    order.status = target_status
    return None


def transition_payment(payment: Payment, target_status: PaymentStatus) -> TransitionError | None:
    if payment.status == target_status:
        return None

    allowed = ALLOWED_PAYMENT_TRANSITIONS.get(payment.status, set())
    if target_status not in allowed:
        return TransitionError(
            "invalid_payment_transition",
            f"Payment cannot transition from {payment.status.value} to {target_status.value}.",
        )

    payment.status = target_status
    return None
