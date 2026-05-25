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
    name = db.Column(db.String(160), nullable=False, default="")
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    usage = db.Column(db.String(40), nullable=False, default="Single use")
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

    offers = db.relationship(
        "Offer",
        secondary="promo_code_offers",
        lazy="selectin",
    )

    @property
    def discount_value_amount(self) -> str:
        return f"{Decimal(self.discount_value):.2f}"

    @property
    def minimum_order_amount_value(self) -> str:
        return f"{Decimal(self.minimum_order_amount):.2f}"


promo_code_offers = db.Table(
    "promo_code_offers",
    db.Column("promo_code_id", db.Integer, db.ForeignKey("promo_codes.id"), primary_key=True),
    db.Column("offer_id", db.Integer, db.ForeignKey("offers.id"), primary_key=True),
)
