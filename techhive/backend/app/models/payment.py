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
    MPESA = "mpesa"
    STRIPE = "stripe"
    FLUTTERWAVE = "flutterwave"
    PAYPAL = "paypal"


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
    external_reference = db.Column(db.String(120), nullable=True, unique=True, index=True)
    provider_event_id = db.Column(db.String(120), nullable=True, unique=True, index=True)
    payer_phone_number = db.Column(db.String(30), nullable=True)
    provider_receipt = db.Column(db.String(120), nullable=True, unique=True, index=True)
    redirect_url = db.Column(db.String(500), nullable=True)
    initiated_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    reconciliation_due_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    reconciliation_attempts = db.Column(db.Integer, nullable=False, default=0)
    failure_code = db.Column(db.String(80), nullable=True, index=True)
    failure_message = db.Column(db.String(255), nullable=True)
    provider_response = db.Column(db.Text, nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
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
