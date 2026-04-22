from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True,
    )
    product_name = db.Column(db.String(180), nullable=False)
    product_slug = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")

    @property
    def unit_price_amount(self) -> str:
        return f"{Decimal(self.unit_price):.2f}"

    @property
    def line_total_amount(self) -> str:
        return f"{Decimal(self.line_total):.2f}"
