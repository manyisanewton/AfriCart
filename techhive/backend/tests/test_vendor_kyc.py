from app.extensions import db
from app.models import User, UserRole, Vendor, VendorKYCStatus, VendorStatus
from tests.factories import create_admin_headers as create_admin_headers_base


def create_vendor_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "vendor-kyc@example.com",
            "password": "SecurePass123",
            "first_name": "Vendor",
            "last_name": "Kyc",
            "phone_number": "+254744000111",
        },
    )
    user = User.query.filter_by(email="vendor-kyc@example.com").first()
    user.role = UserRole.VENDOR
    vendor = Vendor(
        user_id=user.id,
        business_name="KYC Vendor",
        slug="kyc-vendor",
        phone_number="+254744000111",
        support_email="support@kycvendor.com",
        status=VendorStatus.PENDING,
        is_verified=False,
    )
    db.session.add(vendor)
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, vendor


def create_admin_headers(client):
    return create_admin_headers_base(
        client,
        email="admin-kyc@example.com",
        first_name="Admin",
        last_name="Kyc",
        phone_number="+254744000222",
    )


def kyc_payload(**overrides):
    payload = {
        "legal_business_name": "KYC Vendor Ltd",
        "registration_number": "PVT-12345",
        "tax_id": "A123456789X",
        "contact_person_name": "Vendor Kyc",
        "contact_person_id_number": "12345678",
        "document_url": "https://example.com/documents/kyc.pdf",
    }
    payload.update(overrides)
    return payload


def test_vendor_can_submit_and_view_kyc(client):
    headers, _vendor = create_vendor_headers(client)

    submit_response = client.post("/api/v1/vendor/kyc", json=kyc_payload(), headers=headers)
    get_response = client.get("/api/v1/vendor/kyc", headers=headers)

    assert submit_response.status_code == 201
    assert submit_response.get_json()["item"]["status"] == VendorKYCStatus.PENDING.value
    assert get_response.status_code == 200
    assert get_response.get_json()["item"]["registration_number"] == "PVT-12345"


def test_vendor_profile_includes_kyc_status(client):
    headers, _vendor = create_vendor_headers(client)
    client.post("/api/v1/vendor/kyc", json=kyc_payload(), headers=headers)

    response = client.get("/api/v1/vendor/profile", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["kyc_status"] == VendorKYCStatus.PENDING.value


def test_admin_can_review_vendor_kyc_submission(client):
    vendor_headers, _vendor = create_vendor_headers(client)
    admin_headers = create_admin_headers(client)
    submit_response = client.post("/api/v1/vendor/kyc", json=kyc_payload(), headers=vendor_headers)
    submission_id = submit_response.get_json()["item"]["id"]

    review_response = client.patch(
        f"/api/v1/admin/kyc-submissions/{submission_id}/status",
        json={"status": "approved", "admin_note": "Looks good."},
        headers=admin_headers,
    )

    assert review_response.status_code == 200
    assert review_response.get_json()["item"]["status"] == VendorKYCStatus.APPROVED.value
    assert review_response.get_json()["item"]["admin_note"] == "Looks good."


def test_admin_can_list_vendor_kyc_submissions(client):
    vendor_headers, _vendor = create_vendor_headers(client)
    admin_headers = create_admin_headers(client)
    client.post("/api/v1/vendor/kyc", json=kyc_payload(), headers=vendor_headers)

    response = client.get("/api/v1/admin/kyc-submissions", headers=admin_headers)

    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 1
