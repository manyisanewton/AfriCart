from datetime import datetime, timezone
from enum import Enum

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VendorKYCStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VendorKYCSubmission(db.Model):
    __tablename__ = "vendor_kyc_submissions"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False, unique=True, index=True)
    legal_business_name = db.Column(db.String(200), nullable=False)
    registration_number = db.Column(db.String(120), nullable=False)
    tax_id = db.Column(db.String(120), nullable=True)
    contact_person_name = db.Column(db.String(200), nullable=False)
    contact_person_id_number = db.Column(db.String(120), nullable=False)
    document_url = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(VendorKYCStatus, name="vendor_kyc_status"),
        nullable=False,
        default=VendorKYCStatus.PENDING,
    )
    admin_note = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    vendor = db.relationship("Vendor", back_populates="kyc_submission")
