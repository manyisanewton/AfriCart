from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RefundStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class Refund(db.Model):
    __tablename__ = "refunds"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum(RefundStatus, name="refund_status"),
        nullable=False,
        default=RefundStatus.REQUESTED,
    )
    admin_note = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", back_populates="refunds")

    @property
    def amount_value(self) -> str:
        return f"{Decimal(self.amount):.2f}"
