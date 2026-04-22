from decimal import Decimal


def build_invoice_payload(order) -> dict:
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "customer_name": order.shipping_name,
        "currency": order.currency,
        "subtotal": f"{Decimal(order.subtotal):.2f}",
        "shipping_amount": f"{Decimal(order.shipping_amount):.2f}",
        "discount_amount": f"{Decimal(order.discount_amount):.2f}",
        "total_amount": f"{Decimal(order.total_amount):.2f}",
    }
