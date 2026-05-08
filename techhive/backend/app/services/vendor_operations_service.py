from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.models import Order, OrderItem, OrderStatus, Payment, PaymentStatus, Product, Vendor
from app.services.analytics_service import vendor_summary, vendor_top_products


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def export_vendor_catalog(vendor: Vendor) -> dict:
    products = (
        Product.query.filter_by(vendor_id=vendor.id)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .all()
    )
    items = []
    for product in products:
        items.append(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "sku": product.sku,
                "category_id": product.category_id,
                "brand_id": product.brand_id,
                "price": product.price_amount,
                "stock_quantity": product.stock_quantity,
                "short_description": product.short_description,
                "description": product.description,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "variants": [
                    {
                        "id": variant.id,
                        "name": variant.name,
                        "sku": variant.sku,
                        "price": variant.price_amount,
                        "stock_quantity": variant.stock_quantity,
                        "attribute_summary": variant.attribute_summary,
                    }
                    for variant in product.variants
                ],
                "images": [
                    {
                        "id": image.id,
                        "image_url": image.image_url,
                        "alt_text": image.alt_text,
                        "is_primary": image.is_primary,
                        "sort_order": image.sort_order,
                    }
                    for image in product.images
                ],
            }
        )
    return {
        "summary": {
            "product_count": len(items),
            "active_count": sum(1 for item in items if item["is_active"]),
            "featured_count": sum(1 for item in items if item["is_featured"]),
        },
        "items": items,
    }


def build_vendor_analytics_report(vendor: Vendor) -> dict:
    products = Product.query.filter_by(vendor_id=vendor.id).all()
    product_ids = [product.id for product in products]
    order_items = OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all() if product_ids else []
    orders_by_id = {item.order_id: item.order for item in order_items if item.order is not None}
    order_status_counts = Counter(order.status.value for order in orders_by_id.values())
    payments = (
        Payment.query.join(Order, Payment.order)
        .filter(Order.id.in_(orders_by_id.keys()))
        .all()
        if orders_by_id
        else []
    )
    payment_status_counts = Counter(payment.status.value for payment in payments)

    recent_orders = sorted(
        orders_by_id.values(),
        key=lambda order: (order.created_at, order.id),
        reverse=True,
    )[:5]

    low_stock_products = sorted(
        [product for product in products if product.stock_quantity <= 5],
        key=lambda product: (product.stock_quantity, product.id),
    )[:5]

    return {
        "summary": vendor_summary(vendor.id),
        "top_products": vendor_top_products(vendor.id, limit=5),
        "order_status_breakdown": dict(order_status_counts),
        "payment_status_breakdown": dict(payment_status_counts),
        "recent_order_ids": [order.id for order in recent_orders],
        "low_stock_product_ids": [product.id for product in low_stock_products],
    }


def build_vendor_payout_summary(vendor: Vendor) -> dict:
    products = Product.query.filter_by(vendor_id=vendor.id).all()
    product_ids = [product.id for product in products]
    if not product_ids:
        return {
            "gross_revenue": "0.00",
            "paid_revenue": "0.00",
            "ready_for_payout": "0.00",
            "pending_clearance": "0.00",
            "failed_payment_amount": "0.00",
            "eligible_order_count": 0,
            "recent_eligible_order_ids": [],
        }

    order_items = OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all()
    order_item_totals = Counter()
    order_ids = set()
    for item in order_items:
        order_ids.add(item.order_id)
        order_item_totals[item.order_id] += Decimal(item.line_total)

    orders = {order.id: order for order in Order.query.filter(Order.id.in_(order_ids)).all()} if order_ids else {}
    payments = (
        Payment.query.filter(Payment.order_id.in_(order_ids)).all()
        if order_ids
        else []
    )
    payments_by_order = {}
    for payment in payments:
        payments_by_order.setdefault(payment.order_id, []).append(payment)

    gross_revenue = Decimal("0.00")
    paid_revenue = Decimal("0.00")
    ready_for_payout = Decimal("0.00")
    pending_clearance = Decimal("0.00")
    failed_payment_amount = Decimal("0.00")
    eligible_order_ids = []

    for order_id, line_total in order_item_totals.items():
        gross_revenue += line_total
        order = orders.get(order_id)
        order_payments = payments_by_order.get(order_id, [])
        has_paid = any(payment.status == PaymentStatus.PAID for payment in order_payments)
        has_failed = any(payment.status == PaymentStatus.FAILED for payment in order_payments)

        if has_paid:
            paid_revenue += line_total
            if order is not None and order.status == OrderStatus.DELIVERED:
                ready_for_payout += line_total
                eligible_order_ids.append(order_id)
            else:
                pending_clearance += line_total
        elif has_failed:
            failed_payment_amount += line_total
        else:
            pending_clearance += line_total

    recent_eligible_orders = sorted(
        [orders[order_id] for order_id in eligible_order_ids if order_id in orders],
        key=lambda order: (order.created_at, order.id),
        reverse=True,
    )[:5]

    return {
        "gross_revenue": _money(gross_revenue),
        "paid_revenue": _money(paid_revenue),
        "ready_for_payout": _money(ready_for_payout),
        "pending_clearance": _money(pending_clearance),
        "failed_payment_amount": _money(failed_payment_amount),
        "eligible_order_count": len(eligible_order_ids),
        "recent_eligible_order_ids": [order.id for order in recent_eligible_orders],
    }
