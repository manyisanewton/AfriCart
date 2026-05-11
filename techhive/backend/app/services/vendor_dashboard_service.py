from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.blueprints.notifications.routes import serialize_notification
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.products.schemas import serialize_product
from app.models import Notification, Order, OrderItem, OrderStatus, PaymentStatus, Product
from app.services.analytics_service import vendor_top_products
from app.services.dashboard_service import build_section, utc_now_iso
from app.services.vendor_product_service import list_low_stock_products


LOW_STOCK_THRESHOLD = 5
RECENT_LIMIT = 5


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def _is_recent(value: datetime | None, cutoff: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value >= cutoff


def _vendor_orders_query(vendor_id: int):
    return (
        Order.query.join(OrderItem, Order.items)
        .join(Product, OrderItem.product)
        .filter(Product.vendor_id == vendor_id)
        .distinct()
    )


def _vendor_order_items_query(vendor_id: int):
    return (
        OrderItem.query.join(Product, OrderItem.product)
        .join(Order, OrderItem.order)
        .filter(Product.vendor_id == vendor_id)
    )


def build_vendor_dashboard(vendor) -> dict:
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=30)

    products = (
        Product.query.filter_by(vendor_id=vendor.id)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .all()
    )
    product_count = len(products)
    active_product_count = sum(1 for product in products if product.is_active)
    low_stock_products = list_low_stock_products(vendor=vendor, threshold=LOW_STOCK_THRESHOLD)

    orders_query = _vendor_orders_query(vendor.id)
    all_vendor_orders = orders_query.order_by(Order.created_at.desc(), Order.id.desc()).all()
    recent_orders = all_vendor_orders[:RECENT_LIMIT]
    pending_orders_count = sum(1 for order in all_vendor_orders if order.status == OrderStatus.PENDING)
    paid_orders_count = sum(
        1
        for order in all_vendor_orders
        if any(payment.status == PaymentStatus.PAID for payment in order.payments)
    )

    order_items = _vendor_order_items_query(vendor.id).all()
    total_revenue = sum(Decimal(item.line_total) for item in order_items)
    recent_revenue = sum(
        Decimal(item.line_total)
        for item in order_items
        if _is_recent(item.order.created_at, recent_cutoff)
    )

    notifications = (
        Notification.query.filter_by(user_id=vendor.user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    unread_notification_count = sum(0 if notification.is_read else 1 for notification in notifications)
    latest_notifications = notifications[:RECENT_LIMIT]

    base_vendor_products_link = "/api/v1/vendor/products"

    return {
        "persona": "vendor",
        "generated_at": utc_now_iso(),
        "summary": {
            "vendor_id": vendor.id,
            "business_name": vendor.business_name,
            "status": vendor.status.value,
            "kyc_status": (
                vendor.kyc_submission.status.value
                if vendor.kyc_submission is not None
                else "not_submitted"
            ),
            "product_count": product_count,
            "active_product_count": active_product_count,
            "low_stock_count": len(low_stock_products),
            "recent_orders_count": len(recent_orders),
            "pending_orders_count": pending_orders_count,
            "paid_orders_count": paid_orders_count,
            "links": {
                "profile": "/api/v1/vendor/profile",
                "products": base_vendor_products_link,
                "orders": "/api/v1/vendor/orders",
                "low_stock": f"/api/v1/vendor/inventory/low-stock?threshold={LOW_STOCK_THRESHOLD}",
                "analytics": "/api/v1/vendor/analytics/summary",
            },
        },
        "sales": build_section(
            links={
                "analytics_summary": "/api/v1/vendor/analytics/summary",
                "top_products": "/api/v1/vendor/analytics/top-products",
                "orders": "/api/v1/vendor/orders",
            },
            items=[
                {
                    **item,
                    "links": {
                        "product": f"/api/v1/vendor/products/{item['product_id']}",
                    },
                }
                for item in vendor_top_products(vendor.id, limit=RECENT_LIMIT)
            ],
            total_count=len(vendor_top_products(vendor.id, limit=1000)),
            limit=RECENT_LIMIT,
            empty_message="No product sales signals yet.",
            total_orders=len(all_vendor_orders),
            total_revenue=_money(total_revenue),
            recent_revenue=_money(recent_revenue),
            top_products=[
                {
                    **item,
                    "links": {
                        "product": f"/api/v1/vendor/products/{item['product_id']}",
                    },
                }
                for item in vendor_top_products(vendor.id, limit=RECENT_LIMIT)
            ],
        ),
        "inventory": build_section(
            links={
                "all_products": base_vendor_products_link,
                "low_stock": f"/api/v1/vendor/inventory/low-stock?threshold={LOW_STOCK_THRESHOLD}",
            },
            items=[
                {
                    **serialize_product(product, include_related=True),
                    "links": {
                        "product": f"/api/v1/vendor/products/{product.id}",
                    },
                }
                for product in low_stock_products[:RECENT_LIMIT]
            ],
            total_count=len(low_stock_products),
            limit=RECENT_LIMIT,
            empty_message="No low-stock items right now.",
            threshold=LOW_STOCK_THRESHOLD,
            low_stock_items=[
                {
                    **serialize_product(product, include_related=True),
                    "links": {
                        "product": f"/api/v1/vendor/products/{product.id}",
                    },
                }
                for product in low_stock_products[:RECENT_LIMIT]
            ],
        ),
        "orders": build_section(
            links={
                "all_orders": "/api/v1/vendor/orders",
            },
            items=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {
                        "orders": "/api/v1/vendor/orders",
                    },
                }
                for order in recent_orders
            ],
            total_count=len(all_vendor_orders),
            limit=RECENT_LIMIT,
            empty_message="No vendor orders yet.",
            recent=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {
                        "orders": "/api/v1/vendor/orders",
                    },
                }
                for order in recent_orders
            ],
        ),
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
            unread_count=unread_notification_count,
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
    }
