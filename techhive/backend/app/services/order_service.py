from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.blueprints.delivery.tracking import generate_tracking_token
from app.blueprints.orders.helpers import generate_order_number
from app.blueprints.promotions.helpers import validate_promo_code_for_amount
from app.services.commerce_state_service import transition_order
from app.services.delivery_pricing_service import quote_delivery
from app.extensions import db
from app.models import Address, CartItem, NotificationType, Order, OrderItem, OrderStatus, PaymentStatus, Product, PromoCode, Refund, RefundStatus, User
from app.services.notification_dispatch_service import dispatch_user_notification
from app.services.major_notification_service import notify_refund_requested
from app.utils.helpers import format_money


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def get_user_order(*, user_id: int, order_id: int) -> Order | None:
    return Order.query.filter_by(id=order_id, user_id=user_id).first()


def get_order_for_tracking_token(*, tracking_token: str) -> Order | None:
    return Order.query.filter_by(tracking_token=tracking_token).first()


def _dispatch_order_created_notification(order: Order) -> None:
    if order.user is None:
        return
    dispatch_user_notification(
        user=order.user,
        notification_type=NotificationType.ORDER_CREATED,
        title="Order placed",
        message=f"Your order {order.order_number} has been created successfully.",
        email_subject=f"Order {order.order_number} confirmed",
        email_template="order_confirmation",
        email_context={
            "order_number": order.order_number,
            "total_amount": format_money(order.total_amount),
            "headline": "Your order is confirmed",
            "preheader": f"Order {order.order_number} has been received and is being prepared.",
        },
        sms_message=f"TechHive: order {order.order_number} was placed successfully.",
    )


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

    delivery_quote, quote_error = quote_delivery(
        address={
            "city": address.city,
        },
        items=[(item.product, item.quantity) for item in cart_items],
        delivery_location=None,
    )
    if quote_error:
        return None, ServiceError(quote_error)

    shipping_amount = delivery_quote.shipping_amount
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
        delivery_zone_name=delivery_quote.delivery_zone_name,
        shipping_name=address.recipient_name,
        shipping_phone=address.phone_number,
        shipping_country=address.country,
        shipping_city=address.city,
        shipping_state_or_county=address.state_or_county,
        shipping_postal_code=address.postal_code,
        shipping_address_line_1=address.address_line_1,
        shipping_address_line_2=address.address_line_2,
        delivery_location_label=None,
        delivery_distance_km=delivery_quote.distance_km,
        shipping_weight_grams=delivery_quote.weight_grams,
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

    _dispatch_order_created_notification(order)
    return order, None


def create_checkout_order(
    *,
    user: User | None,
    customer: dict,
    address: dict,
    items: list[dict],
    delivery_location: dict | None,
    notes: str | None,
    promo_code_value: str | None,
) -> tuple[Order | None, ServiceError | None]:
    if not items:
        return None, ServiceError({"items": "At least one cart item is required."})

    normalized_products: list[tuple[Product, int]] = []
    seen_product_ids: set[int] = set()
    for item in items:
        product = Product.query.filter_by(id=item["product_id"], is_active=True).first()
        if product is None:
            return None, ServiceError({"items": f"Product {item['product_id']} was not found."}, status_code=404)
        if item["product_id"] in seen_product_ids:
            return None, ServiceError({"items": "Duplicate products are not allowed in checkout items."})
        seen_product_ids.add(item["product_id"])
        if item["quantity"] > product.stock_quantity:
            return None, ServiceError({"items": f"Insufficient stock for product '{product.name}'."})
        normalized_products.append((product, item["quantity"]))

    subtotal = sum(Decimal(product.price) * quantity for product, quantity in normalized_products)
    promo_code = None
    discount_amount = Decimal("0.00")
    if promo_code_value:
        promo_code = PromoCode.query.filter_by(code=promo_code_value).first()
        discount_amount, error = validate_promo_code_for_amount(promo_code, subtotal)
        if error:
            return None, ServiceError({"promo_code": error})

    delivery_quote, quote_error = quote_delivery(
        address=address,
        items=normalized_products,
        delivery_location=delivery_location,
    )
    if quote_error:
        return None, ServiceError(quote_error)

    shipping_amount = delivery_quote.shipping_amount
    order = Order(
        user_id=user.id if user else None,
        guest_email=customer["email"] if user is None else None,
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
        delivery_zone_name=delivery_quote.delivery_zone_name,
        shipping_name=address["recipient_name"],
        shipping_phone=address["phone_number"],
        shipping_country=address["country"],
        shipping_city=address["city"],
        shipping_state_or_county=address["state_or_county"],
        shipping_postal_code=address["postal_code"],
        shipping_address_line_1=address["address_line_1"],
        shipping_address_line_2=address["address_line_2"],
        delivery_location_label=delivery_location["label"] if delivery_location else None,
        delivery_latitude=delivery_location["latitude"] if delivery_location else None,
        delivery_longitude=delivery_location["longitude"] if delivery_location else None,
        delivery_distance_km=delivery_quote.distance_km,
        shipping_weight_grams=delivery_quote.weight_grams,
        notes=notes,
    )
    order.tracking_token = generate_tracking_token(order.order_number)
    db.session.add(order)
    db.session.flush()

    for product, quantity in normalized_products:
        line_total = Decimal(product.price) * quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                sku=product.sku,
                quantity=quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )
        product.stock_quantity -= quantity

    _dispatch_order_created_notification(order)
    return order, None


def get_checkout_quote(
    *,
    address: dict,
    items: list[dict],
    delivery_location: dict | None,
    promo_code_value: str | None,
) -> tuple[dict | None, ServiceError | None]:
    if not items:
        return None, ServiceError({"items": "At least one cart item is required."})

    normalized_products: list[tuple[Product, int]] = []
    seen_product_ids: set[int] = set()
    for item in items:
        product = Product.query.filter_by(id=item["product_id"], is_active=True).first()
        if product is None:
            return None, ServiceError({"items": f"Product {item['product_id']} was not found."}, status_code=404)
        if item["product_id"] in seen_product_ids:
            return None, ServiceError({"items": "Duplicate products are not allowed in checkout items."})
        seen_product_ids.add(item["product_id"])
        normalized_products.append((product, item["quantity"]))

    subtotal = sum(Decimal(product.price) * quantity for product, quantity in normalized_products)
    promo_code = None
    discount_amount = Decimal("0.00")
    if promo_code_value:
        promo_code = PromoCode.query.filter_by(code=promo_code_value).first()
        discount_amount, error = validate_promo_code_for_amount(promo_code, subtotal)
        if error:
            return None, ServiceError({"promo_code": error})

    delivery_quote, quote_error = quote_delivery(
        address=address,
        items=normalized_products,
        delivery_location=delivery_location,
    )
    if quote_error:
        return None, ServiceError(quote_error)

    total_amount = subtotal - discount_amount + delivery_quote.shipping_amount
    return {
        "currency": "KES",
        "subtotal": f"{subtotal:.2f}",
        "discount_amount": f"{discount_amount:.2f}",
        "shipping_amount": f"{delivery_quote.shipping_amount:.2f}",
        "total_amount": f"{total_amount:.2f}",
        "delivery_zone_name": delivery_quote.delivery_zone_name,
        "delivery_method": delivery_quote.method,
        "delivery_location": {
            "label": delivery_location["label"] if delivery_location else None,
            "latitude": delivery_location["latitude"] if delivery_location else None,
            "longitude": delivery_location["longitude"] if delivery_location else None,
            "distance_km": float(delivery_quote.distance_km) if delivery_quote.distance_km is not None else None,
        },
        "shipping_weight_grams": delivery_quote.weight_grams,
        "charges": {
            "base_fee": f"{delivery_quote.base_fee:.2f}",
            "distance_charge": f"{delivery_quote.distance_charge:.2f}",
            "weight_charge": f"{delivery_quote.weight_charge:.2f}",
        },
    }, None


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
    dispatch_user_notification(
        user=order.user,
        notification_type=NotificationType.ORDER_CANCELLED,
        title="Order cancelled",
        message=f"Your order {order.order_number} has been cancelled.",
        email_subject=f"Order {order.order_number} cancelled",
        email_template="order_status",
        email_context={
            "order_number": order.order_number,
            "status_label": "Cancelled",
            "status_tone": "attention",
            "headline": "Your order was cancelled",
        },
        sms_message=f"TechHive: order {order.order_number} has been cancelled.",
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
    notify_refund_requested(refund)
    return refund, None
