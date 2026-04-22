from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    order_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    status = db.Column(
        db.Enum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
    )
    currency = db.Column(db.String(3), nullable=False, default="KES")
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    promo_code = db.Column(db.String(50), nullable=True)
    shipping_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    delivery_status = db.Column(db.String(40), nullable=False, default="processing")
    tracking_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    delivery_zone_name = db.Column(db.String(120), nullable=True)
    delivery_agent_id = db.Column(
        db.Integer,
        db.ForeignKey("delivery_agents.id"),
        nullable=True,
        index=True,
    )
    shipping_name = db.Column(db.String(200), nullable=False)
    shipping_phone = db.Column(db.String(30), nullable=False)
    shipping_country = db.Column(db.String(100), nullable=False)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state_or_county = db.Column(db.String(100), nullable=True)
    shipping_postal_code = db.Column(db.String(30), nullable=True)
    shipping_address_line_1 = db.Column(db.String(255), nullable=False)
    shipping_address_line_2 = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="orders")
    delivery_agent = db.relationship("DeliveryAgent")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments = db.relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refunds = db.relationship(
        "Refund",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def subtotal_amount(self) -> str:
        return f"{Decimal(self.subtotal):.2f}"

    @property
    def total_amount_value(self) -> str:
        return f"{Decimal(self.total_amount):.2f}"
