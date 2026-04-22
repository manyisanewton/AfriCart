from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def auth_headers(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "payment-user@example.com",
            "password": "SecurePass123",
            "first_name": "Payment",
            "last_name": "User",
            "phone_number": "+254755000111",
        },
    )
    token = register_response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_address_for_registered_user():
    user = User.query.filter_by(email="payment-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Payment User",
        phone_number="+254755000111",
        country="Kenya",
        city="Nairobi",
        state_or_county="Nairobi County",
        postal_code="00100",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_payment_product():
    vendor_user = User(
        email="vendor-payment@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Payments",
        phone_number="+254755000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Payments Tech",
        slug="payments-tech",
        phone_number="+254755000222",
        support_email="support@paymentstech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Audio", slug="audio")
    brand = Brand(name="JBL", slug="jbl")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="JBL Charge 5",
        slug="jbl-charge-5",
        sku="JBL-CHARGE-5",
        price=18500.00,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_order_for_payment(client, headers):
    address = create_address_for_registered_user()
    product = create_payment_product()
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201
    return order_response.get_json()["item"]


def test_create_payment_for_order(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)

    response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["order_id"] == order["id"]
    assert item["status"] == "pending"


def test_list_payments_returns_created_payment(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )

    response = client.get("/api/v1/payments", headers=headers)

    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 1


def test_mark_payment_paid_updates_order_state(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]

    response = client.post(f"/api/v1/payments/{payment_id}/mark-paid", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "paid"

    order_response = client.get(f"/api/v1/orders/{order['id']}", headers=headers)
    assert order_response.status_code == 200
    assert order_response.get_json()["item"]["status"] == "confirmed"


def test_mark_payment_failed(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]

    response = client.post(f"/api/v1/payments/{payment_id}/mark-failed", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "failed"
