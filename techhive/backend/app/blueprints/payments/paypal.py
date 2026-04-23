from app.models import Payment


def create_paypal_order(payment: Payment, callback_base_url: str) -> dict:
    return {
        "provider": "paypal",
        "order_id": f"paypal-{payment.reference.lower()}",
        "webhook_url": f"{callback_base_url}/paypal",
        "redirect_url": f"https://www.sandbox.paypal.com/checkoutnow?token={payment.reference}",
    }
