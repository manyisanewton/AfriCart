from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductView(db.Model):
    __tablename__ = "product_views"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    view_count = db.Column(db.Integer, nullable=False, default=1)
    first_viewed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    last_viewed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_product_views_user_product"),
    )

    user = db.relationship("User")
    product = db.relationship("Product")
