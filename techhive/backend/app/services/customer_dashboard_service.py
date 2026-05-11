from __future__ import annotations

from app.blueprints.notifications.routes import serialize_notification
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.payments.helpers import serialize_payment
from app.blueprints.products.schemas import serialize_product
from app.models import Address, Notification, Order, Payment, WishlistItem
from app.services.dashboard_service import build_section, utc_now_iso
from app.services.recommendation_service import personalized_recommendation_items


RECENT_LIMIT = 5
RECOMMENDATION_LIMIT = 6


def _serialize_address(address: Address | None) -> dict | None:
    if address is None:
        return None
    return {
        "id": address.id,
        "label": address.label,
        "recipient_name": address.recipient_name,
        "phone_number": address.phone_number,
        "country": address.country,
        "city": address.city,
        "state_or_county": address.state_or_county,
        "postal_code": address.postal_code,
        "address_line_1": address.address_line_1,
        "address_line_2": address.address_line_2,
        "is_default": address.is_default,
    }


def build_customer_dashboard(user) -> dict:
    orders = (
        Order.query.filter_by(user_id=user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )
    recent_orders = orders[:RECENT_LIMIT]
    payments = (
        Payment.query.join(Order, Payment.order)
        .filter(Order.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .all()
    )
    recent_payments = payments[:RECENT_LIMIT]
    addresses = (
        Address.query.filter_by(user_id=user.id)
        .order_by(Address.is_default.desc(), Address.created_at.desc(), Address.id.desc())
        .all()
    )
    default_address = next((address for address in addresses if address.is_default), addresses[0] if addresses else None)
    notifications = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    latest_notifications = notifications[:RECENT_LIMIT]
    unread_notification_count = sum(0 if notification.is_read else 1 for notification in notifications)
    wishlist_count = WishlistItem.query.filter_by(user_id=user.id).count()
    recommendations = personalized_recommendation_items(user.id, limit=RECOMMENDATION_LIMIT)

    return {
        "persona": "customer",
        "generated_at": utc_now_iso(),
        "summary": {
            "order_count": len(orders),
            "pending_order_count": sum(1 for order in orders if order.status.value == "pending"),
            "address_count": len(addresses),
            "wishlist_count": wishlist_count,
            "unread_notification_count": unread_notification_count,
            "links": {
                "orders": "/api/v1/orders",
                "addresses": "/api/v1/addresses",
                "wishlist": "/api/v1/wishlist",
                "notifications": "/api/v1/notifications",
                "recommendations": "/api/v1/products/recommendations",
            },
        },
        "orders": build_section(
            links={
                "all_orders": "/api/v1/orders",
            },
            items=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {
                        "order": f"/api/v1/orders/{order.id}",
                        "orders": "/api/v1/orders",
                    },
                }
                for order in recent_orders
            ],
            total_count=len(orders),
            limit=RECENT_LIMIT,
            empty_message="No orders yet.",
            recent=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {
                        "order": f"/api/v1/orders/{order.id}",
                        "orders": "/api/v1/orders",
                    },
                }
                for order in recent_orders
            ],
        ),
        "payments": build_section(
            links={
                "all_payments": "/api/v1/payments",
            },
            items=[
                {
                    **serialize_payment(payment),
                    "links": {
                        "payments": "/api/v1/payments",
                        "order": f"/api/v1/orders/{payment.order_id}",
                    },
                }
                for payment in recent_payments
            ],
            total_count=len(payments),
            limit=RECENT_LIMIT,
            empty_message="No payments yet.",
            recent=[
                {
                    **serialize_payment(payment),
                    "links": {
                        "payments": "/api/v1/payments",
                        "order": f"/api/v1/orders/{payment.order_id}",
                    },
                }
                for payment in recent_payments
            ],
        ),
        "addresses": {
            "default": _serialize_address(default_address),
            "links": {
                "addresses": "/api/v1/addresses",
            },
        },
        "notifications": build_section(
            links={
                "notifications": "/api/v1/notifications",
                "preferences": "/api/v1/notifications/preferences",
                "deliveries": "/api/v1/notifications/deliveries",
            },
            items=[
                {
                    **serialize_notification(notification),
                    "links": {
                        "notifications": "/api/v1/notifications",
                    },
                }
                for notification in latest_notifications
            ],
            total_count=len(notifications),
            limit=RECENT_LIMIT,
            empty_message="No notifications yet.",
            latest=[
                {
                    **serialize_notification(notification),
                    "links": {
                        "notifications": "/api/v1/notifications",
                    },
                }
                for notification in latest_notifications
            ],
        ),
        "recommendations": build_section(
            links={
                "recommendations": "/api/v1/products/recommendations",
                "catalog": "/api/v1/products",
            },
            items=[
                {
                    **serialize_product(item["product"]),
                    "reason_code": item["reason_code"],
                    "reason_label": item["reason_label"],
                    "links": {
                        "product": f"/api/v1/products/{item['product'].slug}",
                        "recommendations": "/api/v1/products/recommendations",
                    },
                }
                for item in recommendations
            ],
            total_count=len(recommendations),
            limit=RECOMMENDATION_LIMIT,
            empty_message="No recommendations yet.",
        ),
    }
