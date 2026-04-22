from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class PaymentMethod(str, Enum):
    MANUAL = "manual"
    CASH_ON_DELIVERY = "cash_on_delivery"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    reference = db.Column(db.String(60), nullable=False, unique=True, index=True)
    method = db.Column(
        db.Enum(PaymentMethod, name="payment_method"),
        nullable=False,
        default=PaymentMethod.MANUAL,
    )
    status = db.Column(
        db.Enum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="KES")
    provider_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    order = db.relationship("Order", back_populates="payments")

    @property
    def amount_value(self) -> str:
        return f"{Decimal(self.amount):.2f}"
