from app.models import Payment


def create_stripe_payment_intent(payment: Payment, callback_base_url: str) -> dict:
    return {
        "provider": "stripe",
        "payment_intent_id": f"pi_{payment.reference.lower()}",
        "client_secret": f"cs_{payment.reference.lower()}",
        "webhook_url": f"{callback_base_url}/stripe",
        "redirect_url": f"https://checkout.stripe.test/pay/{payment.reference}",
    }
