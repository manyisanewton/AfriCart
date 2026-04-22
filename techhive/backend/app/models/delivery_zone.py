from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeliveryZone(db.Model):
    __tablename__ = "delivery_zones"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    city = db.Column(db.String(100), nullable=False, unique=True, index=True)
    fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_days_min = db.Column(db.Integer, nullable=False, default=1)
    estimated_days_max = db.Column(db.Integer, nullable=False, default=3)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    @property
    def fee_amount(self) -> str:
        return f"{Decimal(self.fee):.2f}"
