from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductType(db.Model):
    __tablename__ = "product_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False, unique=True)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    requires_shipping = db.Column(db.Boolean, nullable=False, default=True)
    track_stock = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    attributes = db.relationship(
        "ProductAttribute",
        back_populates="product_type",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductAttribute.name.asc()",
    )
