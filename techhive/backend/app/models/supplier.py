from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SupplierStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"), nullable=True, index=True)
    company_name = db.Column(db.String(180), nullable=False)
    contact_name = db.Column(db.String(180), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    country_code = db.Column(db.String(8), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(SupplierStatus, name="supplier_status"),
        nullable=False,
        default=SupplierStatus.PENDING,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="supplier_profile")
    partner = db.relationship("Partner", back_populates="suppliers")
