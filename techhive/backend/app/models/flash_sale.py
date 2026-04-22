from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FlashSale(db.Model):
    __tablename__ = "flash_sales"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    sale_price = db.Column(db.Numeric(12, 2), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    product = db.relationship("Product", back_populates="flash_sales")

    @property
    def sale_price_amount(self) -> str:
        return f"{Decimal(self.sale_price):.2f}"
