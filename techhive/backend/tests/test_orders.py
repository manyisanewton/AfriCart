from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def auth_headers(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "order-user@example.com",
            "password": "SecurePass123",
            "first_name": "Order",
            "last_name": "User",
            "phone_number": "+254744000111",
        },
    )
    token = register_response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_address_for_registered_user():
    user = User.query.filter_by(email="order-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Order User",
        phone_number="+254744000111",
        country="Kenya",
        city="Nairobi",
        state_or_county="Nairobi County",
        postal_code="00100",
        address_line_1="Kenyatta Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_order_product():
    vendor_user = User(
        email="vendor-order@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Orders",
        phone_number="+254744000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Orders Tech",
        slug="orders-tech",
        phone_number="+254744000222",
        support_email="support@orderstech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Tablets", slug="tablets")
    brand = Brand(name="Lenovo", slug="lenovo")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name='Lenovo Tab P12',
        slug='lenovo-tab-p12',
        sku='LENOVO-TAB-P12',
        price=42000.00,
        stock_quantity=4,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def add_item_to_cart(client, headers, product_id, quantity=1):
    return client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


def test_create_order_from_cart(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()
    product = create_order_product()
    add_item_to_cart(client, headers, product.id, quantity=2)

    response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id, "notes": "Please call on arrival."},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["status"] == "pending"
    assert payload["subtotal"] == "84000.00"
    assert len(payload["items"]) == 1


def test_create_order_rejects_empty_cart(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()

    response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["cart"] == "Cart is empty."


def test_list_orders_returns_created_order(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()
    product = create_order_product()
    add_item_to_cart(client, headers, product.id, quantity=1)
    client.post("/api/v1/orders", json={"address_id": address.id}, headers=headers)

    response = client.get("/api/v1/orders", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending"


def test_get_order_returns_order_detail(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()
    product = create_order_product()
    create_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert create_response.status_code == 201
    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    order_id = order_response.get_json()["item"]["id"]

    response = client.get(f"/api/v1/orders/{order_id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["id"] == order_id


def test_cancel_pending_order(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()
    product = create_order_product()
    add_item_to_cart(client, headers, product.id, quantity=1)
    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    order_id = order_response.get_json()["item"]["id"]

    response = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "cancelled"
