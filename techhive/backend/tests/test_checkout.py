from tests.factories import (
    create_catalog_dependencies,
    create_product,
    create_admin_headers,
    create_vendor_user_and_headers,
    register_user_and_headers,
)


def create_checkout_product(client):
    _vendor_headers, vendor = create_vendor_user_and_headers(
        client,
        email="vendor-checkout@example.com",
        first_name="Vendor",
        last_name="Checkout",
        phone_number="+254700123123",
        business_name="Checkout Vendor",
        slug="checkout-vendor",
        support_email="support@checkoutvendor.com",
    )
    category, brand = create_catalog_dependencies(
        category_name="Checkout Phones",
        category_slug="checkout-phones",
        brand_name="Checkout Brand",
        brand_slug="checkout-brand",
    )
    return create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Checkout Test Phone",
        slug="checkout-test-phone",
        sku="CHECKOUT-PHONE-001",
        price=1500.00,
        stock_quantity=10,
        weight_grams=1250,
        is_active=True,
    )


def checkout_payload(product_id, *, quantity=2):
    return {
        "customer": {
            "email": "guest@example.com",
            "name": "Guest Buyer",
            "phone_number": "254700111222",
        },
        "address": {
            "recipient_name": "Guest Buyer",
            "phone_number": "254700111222",
            "country": "Kenya",
            "city": "Nairobi",
            "state_or_county": "Nairobi County",
            "postal_code": "00100",
            "address_line_1": "Moi Avenue",
            "address_line_2": "Shop 5",
        },
        "items": [
            {
                "product_id": product_id,
                "quantity": quantity,
            }
        ],
        "notes": "Guest checkout order",
    }


def test_guest_checkout_creates_order_and_can_be_fetched(client):
    product = create_checkout_product(client)

    create_response = client.post(
        "/api/v1/checkout/orders",
        json=checkout_payload(product.id, quantity=2),
    )

    assert create_response.status_code == 201
    order = create_response.get_json()["item"]
    assert order["guest_email"] == "guest@example.com"
    assert order["subtotal"] == "3000.00"
    assert order["status"] == "pending"
    assert len(order["items"]) == 1

    fetch_response = client.get(f"/api/v1/checkout/orders/{order['tracking_token']}")

    assert fetch_response.status_code == 200
    fetched = fetch_response.get_json()["item"]
    assert fetched["id"] == order["id"]
    assert fetched["tracking_token"] == order["tracking_token"]


def test_checkout_rejects_duplicate_product_lines(client):
    product = create_checkout_product(client)
    payload = checkout_payload(product.id, quantity=1)
    payload["items"].append({"product_id": product.id, "quantity": 1})

    response = client.post("/api/v1/checkout/orders", json=payload)

    assert response.status_code == 400
    assert (
        response.get_json()["error"]["details"]["items"]
        == "Duplicate products are not allowed in checkout items."
    )


def test_guest_checkout_payment_uses_tracking_token(client):
    product = create_checkout_product(client)
    order_response = client.post(
        "/api/v1/checkout/orders",
        json=checkout_payload(product.id, quantity=1),
    )
    order = order_response.get_json()["item"]

    payment_response = client.post(
        "/api/v1/checkout/payments",
        json={
            "order_id": order["id"],
            "tracking_token": order["tracking_token"],
            "method": "manual",
        },
    )

    assert payment_response.status_code == 201
    payment = payment_response.get_json()["item"]
    assert payment["order_id"] == order["id"]
    assert payment["method"] == "manual"
    assert payment["status"] == "pending"


def test_authenticated_checkout_attaches_order_to_user(client):
    headers, user = register_user_and_headers(
        client,
        email="signed-in-checkout@example.com",
        first_name="Signed",
        last_name="In",
        phone_number="+254711222333",
    )
    product = create_checkout_product(client)

    response = client.post(
        "/api/v1/checkout/orders",
        json=checkout_payload(product.id, quantity=1),
        headers=headers,
    )

    assert response.status_code == 201
    order = response.get_json()["item"]
    assert order["guest_email"] is None
    user_orders_response = client.get("/api/v1/orders", headers=headers)
    assert user_orders_response.status_code == 200
    assert user_orders_response.get_json()["items"][0]["id"] == order["id"]


def test_checkout_quote_uses_live_location_and_weight_pricing(client):
    admin_headers = create_admin_headers(client)
    product = create_checkout_product(client)

    settings = {
        "delivery.origin_label": "HQ",
        "delivery.origin_latitude": "-1.286389",
        "delivery.origin_longitude": "36.817223",
        "delivery.base_fee": "100",
        "delivery.per_km_fee": "10",
        "delivery.per_kg_fee": "20",
        "delivery.minimum_fee": "100",
        "delivery.free_distance_km": "0",
        "delivery.max_service_distance_km": "100",
    }
    for key, value in settings.items():
        client.post(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json={"key": key, "value": value, "is_public": False},
        )

    payload = checkout_payload(product.id, quantity=2)
    payload["delivery_location"] = {
        "label": "Customer dropoff",
        "latitude": -1.3000,
        "longitude": 36.8000,
    }

    quote_response = client.post("/api/v1/checkout/quote", json=payload)

    assert quote_response.status_code == 200
    quote = quote_response.get_json()["item"]
    assert quote["shipping_weight_grams"] == 2500
    assert quote["delivery_method"] == "distance_weight"
    assert quote["delivery_location"]["distance_km"] is not None
    assert float(quote["shipping_amount"]) > 0
