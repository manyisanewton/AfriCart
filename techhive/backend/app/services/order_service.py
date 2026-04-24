from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.blueprints.delivery.tracking import generate_tracking_token, resolve_delivery_zone
from app.blueprints.notifications.push import create_notification
from app.blueprints.orders.helpers import generate_order_number
from app.blueprints.promotions.helpers import validate_promo_code_for_amount
from app.services.commerce_state_service import transition_order
from app.extensions import db
from app.models import (
    Address,
    CartItem,
    NotificationType,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    PromoCode,
    Refund,
    RefundStatus,
)


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def get_user_order(*, user_id: int, order_id: int) -> Order | None:
    return Order.query.filter_by(id=order_id, user_id=user_id).first()


def create_order_from_cart(
    *,
    user_id: int,
    address_id: int,
    notes: str | None,
    promo_code_value: str | None,
) -> tuple[Order | None, ServiceError | None]:
    address = Address.query.filter_by(id=address_id, user_id=user_id).first()
    if address is None:
        return None, ServiceError({"address_id": "Selected address was not found."})

    cart_items = (
        CartItem.query.filter_by(user_id=user_id)
        .order_by(CartItem.created_at.asc(), CartItem.id.asc())
        .all()
    )
    if not cart_items:
        return None, ServiceError({"cart": "Cart is empty."})

    for cart_item in cart_items:
        if cart_item.quantity > cart_item.product.stock_quantity:
            return None, ServiceError(
                {"cart": f"Insufficient stock for product '{cart_item.product.name}'."}
            )

    subtotal = sum(Decimal(item.product.price) * item.quantity for item in cart_items)
    promo_code = None
    discount_amount = Decimal("0.00")
    if promo_code_value:
        promo_code = PromoCode.query.filter_by(code=promo_code_value).first()
        discount_amount, error = validate_promo_code_for_amount(promo_code, subtotal)
        if error:
            return None, ServiceError({"promo_code": error})

    zone = resolve_delivery_zone(address.city)
    shipping_amount = Decimal(zone.fee) if zone is not None else Decimal("0.00")
    order = Order(
        user_id=user_id,
        order_number=generate_order_number(),
        status=OrderStatus.PENDING,
        currency="KES",
        subtotal=subtotal,
        discount_amount=discount_amount,
        promo_code=promo_code.code if promo_code else None,
        shipping_amount=shipping_amount,
        total_amount=subtotal - discount_amount + shipping_amount,
        delivery_status="processing",
        tracking_token="pending-tracking-token",
        delivery_zone_name=zone.name if zone is not None else None,
        shipping_name=address.recipient_name,
        shipping_phone=address.phone_number,
        shipping_country=address.country,
        shipping_city=address.city,
        shipping_state_or_county=address.state_or_county,
        shipping_postal_code=address.postal_code,
        shipping_address_line_1=address.address_line_1,
        shipping_address_line_2=address.address_line_2,
        notes=notes,
    )
    order.tracking_token = generate_tracking_token(order.order_number)
    db.session.add(order)
    db.session.flush()

    for cart_item in cart_items:
        product = cart_item.product
        line_total = Decimal(product.price) * cart_item.quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                sku=product.sku,
                quantity=cart_item.quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )
        product.stock_quantity -= cart_item.quantity
        db.session.delete(cart_item)

    create_notification(
        user_id,
        NotificationType.ORDER_CREATED,
        "Order placed",
        f"Your order {order.order_number} has been created successfully.",
    )
    return order, None


def cancel_order_for_user(*, user_id: int, order_id: int) -> tuple[Order | None, ServiceError | None]:
    order = get_user_order(user_id=user_id, order_id=order_id)
    if order is None:
        return None, ServiceError({"order": "Order not found."}, status_code=404)

    if order.status != OrderStatus.PENDING:
        return None, ServiceError(
            {"order": "Only pending orders can be cancelled."},
            status_code=400,
        )

    for item in order.items:
        item.product.stock_quantity += item.quantity

    transition_error = transition_order(order, OrderStatus.CANCELLED)
    if transition_error is not None:
        return None, ServiceError({"order": transition_error.message}, status_code=400)
    create_notification(
        user_id,
        NotificationType.ORDER_CANCELLED,
        "Order cancelled",
        f"Your order {order.order_number} has been cancelled.",
    )
    return order, None


def request_refund_for_order(
    *,
    user_id: int,
    order_id: int,
    reason: str,
) -> tuple[Refund | None, ServiceError | None]:
    order = get_user_order(user_id=user_id, order_id=order_id)
    if order is None:
        return None, ServiceError({"order": "Order not found."}, status_code=404)

    if not any(payment.status == PaymentStatus.PAID for payment in order.payments):
        return None, ServiceError({"order": "Refunds can only be requested for paid orders."})

    existing = Refund.query.filter_by(order_id=order.id).filter(
        Refund.status.in_([RefundStatus.REQUESTED, RefundStatus.APPROVED, RefundStatus.PROCESSED])
    ).first()
    if existing is not None:
        return None, ServiceError({"order": "A refund request already exists for this order."})

    refund = Refund(
        order_id=order.id,
        amount=order.total_amount,
        reason=reason,
        status=RefundStatus.REQUESTED,
    )
    db.session.add(refund)
    create_notification(
        user_id,
        NotificationType.ORDER_CANCELLED,
        "Refund requested",
        f"Refund requested for order {order.order_number}.",
    )
    return refund, None
