from datetime import datetime, timezone

from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.vendors import vendors_bp
from app.blueprints.vendors.routes import _vendor_profile_or_403
from app.blueprints.vendors.schemas import (
    serialize_vendor_kyc_submission,
    validate_vendor_kyc_payload,
)
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import UserRole, VendorKYCStatus, VendorKYCSubmission
from app.services.audit_service import log_audit_event


def _add_vendor_kyc_audit_log(*, action: str, submission_id: int, metadata: dict | None = None) -> None:
    db.session.add(
        log_audit_event(
            actor_user_id=g.current_user.id,
            action=action,
            entity_type="vendor_kyc_submission",
            entity_id=submission_id,
            metadata=metadata,
        )
    )


@vendors_bp.get("/kyc")
@role_required(UserRole.VENDOR.value)
def get_vendor_kyc():
    """
    Get the authenticated vendor's KYC submission.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor KYC status.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    submission = vendor.kyc_submission
    if submission is None:
        return jsonify({"item": {"status": VendorKYCStatus.NOT_SUBMITTED.value, "vendor_id": vendor.id}})

    return jsonify({"item": serialize_vendor_kyc_submission(submission)})


@vendors_bp.post("/kyc")
@role_required(UserRole.VENDOR.value)
def submit_vendor_kyc():
    """
    Submit or resubmit vendor KYC details.
    ---
    tags:
      - Vendors
    responses:
      201:
        description: KYC submission saved.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_kyc_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    submission = vendor.kyc_submission
    created = submission is None
    if submission is None:
        submission = VendorKYCSubmission(vendor_id=vendor.id, **payload, status=VendorKYCStatus.PENDING)
        db.session.add(submission)
    else:
        for field, value in payload.items():
            setattr(submission, field, value)
        submission.status = VendorKYCStatus.PENDING
        submission.admin_note = None
        submission.reviewed_at = None

    db.session.flush()
    _add_vendor_kyc_audit_log(
        action="vendor.kyc_submitted",
        submission_id=submission.id,
        metadata={"status": submission.status.value, "vendor_id": vendor.id},
    )
    db.session.commit()
    return jsonify({"item": serialize_vendor_kyc_submission(submission)}), 201 if created else 200
