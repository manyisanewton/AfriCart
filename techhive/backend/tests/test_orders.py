from app.models import User
from tests.factories import (
    create_address_for_user,
    create_catalog_dependencies,
    create_product,
    create_vendor_user_and_headers,
    register_user_and_headers,
)


def auth_headers(client):
    headers, _user = register_user_and_headers(
        client,
        email="order-user@example.com",
        first_name="Order",
        last_name="User",
        phone_number="+254744000111",
    )
    return headers


def create_address_for_registered_user():
    user = User.query.filter_by(email="order-user@example.com").first()
    return create_address_for_user(
        user,
        recipient_name="Order User",
        phone_number="+254744000111",
        state_or_county="Nairobi County",
        postal_code="00100",
        address_line_1="Kenyatta Avenue",
    )
def create_order_product_with_client(client):
    _vendor_headers, vendor = create_vendor_user_and_headers(
        client,
        email="vendor-order@example.com",
        first_name="Vendor",
        last_name="Orders",
        phone_number="+254744000222",
        business_name="Orders Tech",
        slug="orders-tech",
        support_email="support@orderstech.com",
    )
    category, brand = create_catalog_dependencies(
        category_name="Tablets",
        category_slug="tablets",
        brand_name="Lenovo",
        brand_slug="lenovo",
    )
    return create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Lenovo Tab P12",
        slug="lenovo-tab-p12",
        sku="LENOVO-TAB-P12",
        price=42000.00,
        stock_quantity=4,
        is_active=True,
    )


def add_item_to_cart(client, headers, product_id, quantity=1):
    return client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


def test_create_order_from_cart(client):
    headers = auth_headers(client)
    address = create_address_for_registered_user()
    product = create_order_product_with_client(client)
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
    product = create_order_product_with_client(client)
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
    product = create_order_product_with_client(client)
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
    product = create_order_product_with_client(client)
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
