from datetime import datetime, timezone
from decimal import Decimal

from app.models import PromoCode, PromoCodeType


def serialize_promo_code(promo_code: PromoCode) -> dict:
    return {
        "id": promo_code.id,
        "code": promo_code.code,
        "discount_type": promo_code.discount_type.value,
        "discount_value": promo_code.discount_value_amount,
        "minimum_order_amount": promo_code.minimum_order_amount_value,
        "is_active": promo_code.is_active,
        "starts_at": promo_code.starts_at.isoformat() if promo_code.starts_at else None,
        "ends_at": promo_code.ends_at.isoformat() if promo_code.ends_at else None,
    }


def validate_promo_code_for_amount(promo_code: PromoCode | None, subtotal: Decimal):
    if promo_code is None:
        return None, "Promo code was not found."
    if not promo_code.is_active:
        return None, "Promo code is inactive."

    now = datetime.now(timezone.utc)
    if promo_code.starts_at and promo_code.starts_at > now:
        return None, "Promo code is not active yet."
    if promo_code.ends_at and promo_code.ends_at < now:
        return None, "Promo code has expired."
    if subtotal < Decimal(promo_code.minimum_order_amount):
        return None, "Order does not meet the minimum amount for this promo code."

    if promo_code.discount_type == PromoCodeType.PERCENTAGE:
        discount = (subtotal * Decimal(promo_code.discount_value) / Decimal("100")).quantize(
            Decimal("0.01")
        )
    else:
        discount = Decimal(promo_code.discount_value).quantize(Decimal("0.01"))

    if discount > subtotal:
        discount = subtotal

    return discount, None
