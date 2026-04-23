from datetime import datetime, timedelta, timezone

from app.services import payment_reconciliation_service as reconciliation_service
from app.extensions import db
from app.models import Address, Brand, Category, Payment, PaymentMethod, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-slice@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Slice",
            "phone_number": "+254777000111",
        },
    )
    user = User.query.filter_by(email="admin-slice@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "plain-user@example.com",
            "password": "SecurePass123",
            "first_name": "Plain",
            "last_name": "User",
            "phone_number": "+254777000222",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_vendor_fixture():
    vendor_user = User(
        email="admin-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Admin",
        phone_number="+254777000333",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Admin Vendor",
        slug="admin-vendor",
        phone_number="+254777000333",
        support_email="support@adminvendor.com",
        status=VendorStatus.PENDING,
        is_verified=False,
    )
    db.session.add_all([vendor_user, vendor])
    db.session.commit()
    return vendor_user, vendor


def create_product_fixture(vendor):
    category = Category(name="Networking", slug="networking")
    brand = Brand(name="TP-Link", slug="tp-link")
    product = Product(
        vendor_id=vendor.id,
        category=category,
        brand=brand,
        name="TP-Link Archer AX55",
        slug="tp-link-archer-ax55",
        sku="TPLINK-AX55",
        price=16500,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([category, brand, product])
    db.session.commit()
    return product


def create_order_fixture(client):
    customer_headers = create_customer_headers(client)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Plain User",
        phone_number="+254777000222",
        country="Kenya",
        city="Nairobi",
        address_line_1="Ronald Ngala Street",
        is_default=True,
    )
    db.session.add(address)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    db.session.commit()

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=customer_headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=customer_headers,
    )
    assert order_response.status_code == 201
    return order_response.get_json()["item"]


def test_non_admin_cannot_access_admin_users(client):
    headers = create_customer_headers(client)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 403


def test_admin_can_list_users(client):
    headers = create_admin_headers(client)
    create_customer_headers(client)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    assert len(response.get_json()["items"]) >= 2


def test_admin_can_update_user_role(client):
    headers = create_admin_headers(client)
    create_customer_headers(client)
    user = User.query.filter_by(email="plain-user@example.com").first()

    response = client.patch(
        f"/api/v1/admin/users/{user.id}/role",
        json={"role": "vendor"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["role"] == "vendor"


def test_admin_can_approve_vendor(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()

    response = client.patch(
        f"/api/v1/admin/vendors/{vendor.id}/status",
        json={"status": "approved"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "approved"
    assert response.get_json()["item"]["is_verified"] is True


def test_admin_can_create_category_and_brand(client):
    headers = create_admin_headers(client)

    category_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Storage", "slug": "storage"},
        headers=headers,
    )
    brand_response = client.post(
        "/api/v1/admin/brands",
        json={"name": "SanDisk", "slug": "sandisk"},
        headers=headers,
    )

    assert category_response.status_code == 201
    assert brand_response.status_code == 201


def test_admin_can_deactivate_product(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    response = client.patch(
        f"/api/v1/admin/products/{product.id}/active",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["is_active"] is False


def test_admin_can_update_order_status(client):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)

    response = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "processing"


def test_admin_can_reconcile_stale_mpesa_payments(client):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    assert payment_response.status_code == 201
    payment_id = payment_response.get_json()["item"]["id"]

    payment = db.session.get(Payment, payment_id)
    payment.method = PaymentMethod.MPESA
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["awaiting_confirmation_count"] == 1
    assert response.get_json()["timed_out_count"] == 0
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "pending"
    assert item["failure_code"] == "awaiting_provider_confirmation"
    assert item["reconciliation_attempts"] == 1

    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    timeout_response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert timeout_response.status_code == 200
    assert timeout_response.get_json()["awaiting_confirmation_count"] == 0
    assert timeout_response.get_json()["timed_out_count"] == 1
    timed_out_item = timeout_response.get_json()["items"][0]
    assert timed_out_item["id"] == payment_id
    assert timed_out_item["status"] == "failed"
    assert timed_out_item["failure_code"] == "reconciliation_timeout"
    assert timed_out_item["reconciliation_attempts"] == 2


def test_admin_reconciliation_marks_provider_failed_payment(client, monkeypatch):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    monkeypatch.setattr(
        reconciliation_service,
        "query_mpesa_payment_status",
        lambda payment: {
            "state": "failed",
            "failure_code": "insufficient_funds",
            "failure_message": "The M-Pesa account has insufficient funds.",
            "raw": {"provider": "mpesa", "result_code": 1},
        },
    )

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["provider_failed_count"] == 1
    assert response.get_json()["manual_review_count"] == 0
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "failed"
    assert item["failure_code"] == "insufficient_funds"


def test_admin_reconciliation_marks_manual_review_when_provider_reports_success_without_callback(
    client,
    monkeypatch,
):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    monkeypatch.setattr(
        reconciliation_service,
        "query_mpesa_payment_status",
        lambda payment: {
            "state": "manual_review",
            "failure_code": "manual_review_required",
            "failure_message": "M-Pesa reports success, but callback proof is still missing.",
            "raw": {"provider": "mpesa", "result_code": 0},
        },
    )

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["manual_review_count"] == 1
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "pending"
    assert item["failure_code"] == "manual_review_required"
    assert item["reconciliation_due_at"] is None
