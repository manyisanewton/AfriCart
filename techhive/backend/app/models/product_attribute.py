from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductAttribute(db.Model):
    __tablename__ = "product_attributes"

    id = db.Column(db.Integer, primary_key=True)
    product_type_id = db.Column(
        db.Integer,
        db.ForeignKey("product_types.id"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(140), nullable=False)
    code = db.Column(db.String(160), nullable=False)
    type = db.Column(db.String(40), nullable=False, default="text")
    required = db.Column(db.Boolean, nullable=False, default=False)
    option_group_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    product_type = db.relationship("ProductType", back_populates="attributes")
