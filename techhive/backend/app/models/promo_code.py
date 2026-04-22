from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PromoCodeType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class PromoCode(db.Model):
    __tablename__ = "promo_codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    discount_type = db.Column(
        db.Enum(PromoCodeType, name="promo_code_type"),
        nullable=False,
    )
    discount_value = db.Column(db.Numeric(12, 2), nullable=False)
    minimum_order_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    @property
    def discount_value_amount(self) -> str:
        return f"{Decimal(self.discount_value):.2f}"

    @property
    def minimum_order_amount_value(self) -> str:
        return f"{Decimal(self.minimum_order_amount):.2f}"
