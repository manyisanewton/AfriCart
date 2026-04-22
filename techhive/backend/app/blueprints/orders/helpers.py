from datetime import datetime
from decimal import Decimal

from app.models import Order


def generate_order_number() -> str:
    return f"TH-{datetime.utcnow():%Y%m%d%H%M%S%f}"


def serialize_order_item(item) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": item.product_name,
        "product_slug": item.product_slug,
        "sku": item.sku,
        "quantity": item.quantity,
        "unit_price": item.unit_price_amount,
        "line_total": item.line_total_amount,
    }


def serialize_order(order: Order, include_items: bool = False) -> dict:
    payload = {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value,
        "currency": order.currency,
        "subtotal": f"{Decimal(order.subtotal):.2f}",
        "shipping_amount": f"{Decimal(order.shipping_amount):.2f}",
        "total_amount": f"{Decimal(order.total_amount):.2f}",
        "shipping_address": {
            "name": order.shipping_name,
            "phone_number": order.shipping_phone,
            "country": order.shipping_country,
            "city": order.shipping_city,
            "state_or_county": order.shipping_state_or_county,
            "postal_code": order.shipping_postal_code,
            "address_line_1": order.shipping_address_line_1,
            "address_line_2": order.shipping_address_line_2,
        },
        "notes": order.notes,
        "created_at": order.created_at.isoformat(),
    }
    if include_items:
        payload["items"] = [serialize_order_item(item) for item in order.items]
    return payload
