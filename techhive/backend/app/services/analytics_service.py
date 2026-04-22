from decimal import Decimal

from app.models import Order, OrderItem, OrderStatus, Payment, PaymentStatus, Product, User, Vendor


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def admin_summary():
    total_users = User.query.count()
    total_vendors = Vendor.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = (
        sum(Decimal(order.total_amount) for order in Order.query.filter(Order.status != OrderStatus.CANCELLED).all())
        if total_orders
        else Decimal("0.00")
    )
    paid_payments = Payment.query.filter_by(status=PaymentStatus.PAID).count()

    return {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "total_products": total_products,
        "total_orders": total_orders,
        "paid_payments": paid_payments,
        "total_revenue": _money(total_revenue),
    }


def admin_top_products(limit: int = 5):
    rows = (
        OrderItem.query.with_entities(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.product_slug,
            OrderItem.quantity,
            OrderItem.line_total,
        )
        .all()
    )

    aggregates = {}
    for row in rows:
        bucket = aggregates.setdefault(
            row.product_id,
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_slug": row.product_slug,
                "units_sold": 0,
                "revenue": Decimal("0.00"),
            },
        )
        bucket["units_sold"] += row.quantity
        bucket["revenue"] += Decimal(row.line_total)

    ranked = sorted(
        aggregates.values(),
        key=lambda item: (item["units_sold"], item["revenue"]),
        reverse=True,
    )[:limit]

    return [
        {
            **item,
            "revenue": _money(item["revenue"]),
        }
        for item in ranked
    ]


def vendor_summary(vendor_id: int):
    products = Product.query.filter_by(vendor_id=vendor_id).all()
    product_ids = [product.id for product in products]
    product_count = len(products)
    low_stock_count = sum(1 for product in products if product.stock_quantity <= 5)

    if not product_ids:
        return {
            "product_count": 0,
            "low_stock_count": 0,
            "order_count": 0,
            "units_sold": 0,
            "revenue": "0.00",
        }

    order_items = OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all()
    order_ids = {item.order_id for item in order_items}
    units_sold = sum(item.quantity for item in order_items)
    revenue = sum(Decimal(item.line_total) for item in order_items)

    return {
        "product_count": product_count,
        "low_stock_count": low_stock_count,
        "order_count": len(order_ids),
        "units_sold": units_sold,
        "revenue": _money(revenue),
    }


def vendor_top_products(vendor_id: int, limit: int = 5):
    products = Product.query.filter_by(vendor_id=vendor_id).all()
    product_ids = [product.id for product in products]
    if not product_ids:
        return []

    rows = OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all()
    aggregates = {}
    for row in rows:
        bucket = aggregates.setdefault(
            row.product_id,
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_slug": row.product_slug,
                "units_sold": 0,
                "revenue": Decimal("0.00"),
            },
        )
        bucket["units_sold"] += row.quantity
        bucket["revenue"] += Decimal(row.line_total)

    ranked = sorted(
        aggregates.values(),
        key=lambda item: (item["units_sold"], item["revenue"]),
        reverse=True,
    )[:limit]

    return [
        {
            **item,
            "revenue": _money(item["revenue"]),
        }
        for item in ranked
    ]
