from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


product_range_products = db.Table(
    "product_range_products",
    db.Column("range_id", db.Integer, db.ForeignKey("product_ranges.id"), primary_key=True),
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
)


class ProductRange(db.Model):
    __tablename__ = "product_ranges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    includes_all_products = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    products = db.relationship(
        "Product",
        secondary=product_range_products,
        lazy="selectin",
    )
