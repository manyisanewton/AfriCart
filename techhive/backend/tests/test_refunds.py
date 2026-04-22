from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refund-admin@example.com",
            "password": "SecurePass123",
            "first_name": "Refund",
            "last_name": "Admin",
            "phone_number": "+254722220001",
        },
    )
    user = User.query.filter_by(email="refund-admin@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refund-customer@example.com",
            "password": "SecurePass123",
            "first_name": "Refund",
            "last_name": "Customer",
            "phone_number": "+254722220002",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_paid_order(client, customer_headers):
    vendor_user = User(
        email="refund-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Refund",
        last_name="Vendor",
        phone_number="+254722220003",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Refund Tech",
        slug="refund-tech",
        phone_number="+254722220003",
        support_email="support@refundtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Mice", slug="mice")
    brand = Brand(name="Razer", slug="razer")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Razer Basilisk V3",
        slug="razer-basilisk-v3",
        sku="RAZER-BASILISK-V3",
        price=9800.00,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()

    customer = User.query.filter_by(email="refund-customer@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Refund Customer",
        phone_number="+254722220002",
        country="Kenya",
        city="Nairobi",
        address_line_1="Luthuli Avenue",
        is_default=True,
    )
    db.session.add(address)
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
    order = order_response.get_json()["item"]

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=customer_headers,
    )
    assert payment_response.status_code in (200, 201)
    payment = payment_response.get_json()["item"]

    mark_paid = client.post(
        f"/api/v1/payments/{payment['id']}/mark-paid",
        headers=customer_headers,
    )
    assert mark_paid.status_code == 200

    return order


def test_customer_can_request_refund_for_paid_order(client):
    customer_headers = create_customer_headers(client)
    order = create_paid_order(client, customer_headers)

    response = client.post(
        f"/api/v1/orders/{order['id']}/refund-request",
        json={"reason": "Item arrived damaged."},
        headers=customer_headers,
    )

    assert response.status_code == 201
    assert response.get_json()["item"]["status"] == "requested"


def test_customer_cannot_request_duplicate_refund(client):
    customer_headers = create_customer_headers(client)
    order = create_paid_order(client, customer_headers)
    first = client.post(
        f"/api/v1/orders/{order['id']}/refund-request",
        json={"reason": "Item arrived damaged."},
        headers=customer_headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/orders/{order['id']}/refund-request",
        json={"reason": "Still damaged."},
        headers=customer_headers,
    )

    assert second.status_code == 400
    assert second.get_json()["error"]["details"]["order"] == "A refund request already exists for this order."


def test_admin_can_list_and_process_refunds(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    order = create_paid_order(client, customer_headers)
    refund_response = client.post(
        f"/api/v1/orders/{order['id']}/refund-request",
        json={"reason": "Wrong item shipped."},
        headers=customer_headers,
    )
    refund_id = refund_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/refunds", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    process_response = client.patch(
        f"/api/v1/admin/refunds/{refund_id}/status",
        json={"status": "processed", "admin_note": "Refund sent back to customer."},
        headers=admin_headers,
    )

    assert process_response.status_code == 200
    assert process_response.get_json()["item"]["status"] == "processed"
