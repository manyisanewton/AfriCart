from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OfferCondition(db.Model):
    __tablename__ = "offer_conditions"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(80), nullable=False)
    range_id = db.Column(db.Integer, nullable=True)
    value = db.Column(db.String(255), nullable=True)
    proxy_class = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class OfferBenefit(db.Model):
    __tablename__ = "offer_benefits"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(80), nullable=False)
    range_id = db.Column(db.Integer, nullable=True)
    value = db.Column(db.String(255), nullable=True)
    proxy_class = db.Column(db.String(120), nullable=True)
    max_affected_items = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Offer(db.Model):
    __tablename__ = "offers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    offer_type = db.Column(db.String(80), nullable=False)
    exclusive = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(30), nullable=False, default="Open")
    priority = db.Column(db.Integer, nullable=False, default=0)
    start_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    end_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    num_applications = db.Column(db.Integer, nullable=False, default=0)
    num_orders = db.Column(db.Integer, nullable=False, default=0)
    total_discount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    condition_id = db.Column(db.Integer, db.ForeignKey("offer_conditions.id"), nullable=True)
    benefit_id = db.Column(db.Integer, db.ForeignKey("offer_benefits.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    condition = db.relationship("OfferCondition")
    benefit = db.relationship("OfferBenefit")
