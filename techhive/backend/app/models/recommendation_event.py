from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecommendationEvent(db.Model):
    __tablename__ = "recommendation_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    event_type = db.Column(db.String(20), nullable=False, index=True)
    mode = db.Column(db.String(40), nullable=False, index=True)
    reason_code = db.Column(db.String(80), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    user = db.relationship("User")
    product = db.relationship("Product")
