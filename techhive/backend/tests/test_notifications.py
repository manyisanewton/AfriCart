from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "notify-user@example.com",
            "password": "SecurePass123",
            "first_name": "Notify",
            "last_name": "User",
            "phone_number": "+254799000111",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_notification_product():
    vendor_user = User(
        email="vendor-notify@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Notify",
        phone_number="+254799000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Notify Tech",
        slug="notify-tech",
        phone_number="+254799000222",
        support_email="support@notifytech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Projectors", slug="projectors")
    brand = Brand(name="Epson", slug="epson")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Epson EB-FH06",
        slug="epson-eb-fh06",
        sku="EPSON-EB-FH06",
        price=78000.00,
        stock_quantity=3,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_address_for_notification_user():
    user = User.query.filter_by(email="notify-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Notify User",
        phone_number="+254799000111",
        country="Kenya",
        city="Nairobi",
        address_line_1="Haile Selassie Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_order_and_payment(client, headers):
    product = create_notification_product()
    address = create_address_for_notification_user()

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
    order = order_response.get_json()["item"]

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    assert payment_response.status_code in (200, 201)
    payment = payment_response.get_json()["item"]
    return order, payment


def test_notifications_list_includes_order_and_payment_events(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.get("/api/v1/notifications", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total"] >= 2
    assert payload["summary"]["unread_count"] >= 2


def test_mark_single_notification_read(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)
    list_response = client.get("/api/v1/notifications", headers=headers)
    notification_id = list_response.get_json()["items"][0]["id"]

    response = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["is_read"] is True


def test_mark_all_notifications_read(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.post("/api/v1/notifications/read-all", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["updated_count"] >= 2

    list_response = client.get("/api/v1/notifications", headers=headers)
    assert list_response.status_code == 200
    assert list_response.get_json()["summary"]["unread_count"] == 0


def test_payment_paid_creates_notification(client):
    headers = create_customer_headers(client)
    _, payment = create_order_and_payment(client, headers)

    paid_response = client.post(
        f"/api/v1/payments/{payment['id']}/mark-paid",
        headers=headers,
    )
    assert paid_response.status_code == 200

    list_response = client.get("/api/v1/notifications", headers=headers)
    types = [item["type"] for item in list_response.get_json()["items"]]
    assert "payment_paid" in types
