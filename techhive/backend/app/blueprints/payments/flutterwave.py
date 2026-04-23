from app.models import Payment


def create_flutterwave_payment(payment: Payment, callback_base_url: str) -> dict:
    return {
        "provider": "flutterwave",
        "tx_ref": f"flw-{payment.reference.lower()}",
        "webhook_url": f"{callback_base_url}/flutterwave",
        "redirect_url": f"https://checkout.flutterwave.test/pay/{payment.reference}",
    }
