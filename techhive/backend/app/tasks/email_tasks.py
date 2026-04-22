from app.services.email_service import send_email


def send_order_confirmation_email(*, to_email: str, order_number: str, total_amount: str) -> dict:
    return send_email(
        to_email=to_email,
        subject=f"Order {order_number} confirmation",
        template="order_confirmation",
        context={"order_number": order_number, "total_amount": total_amount},
    )
