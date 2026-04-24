from app.extensions import db
from app.models import Address, Product, User
from tests.factories import (
    create_address_for_user,
    create_catalog_dependencies,
    create_product,
    create_customer_headers,
    create_vendor_user_and_headers,
)


def register_customer_headers(client):
    return create_customer_headers(
        client,
        email="customer-vendor-test@example.com",
        first_name="Customer",
        last_name="User",
        phone_number="+254766000111",
    )


def create_vendor_user_and_headers_wrapper(client):
    return create_vendor_user_and_headers(
        client,
        email="vendor-slice@example.com",
        first_name="Vendor",
        last_name="Slice",
        phone_number="+254766000222",
        business_name="Slice Vendor",
        slug="slice-vendor",
        support_email="support@vendor-slice.com",
    )


def test_customer_cannot_access_vendor_profile(client):
    headers = register_customer_headers(client)

    response = client.get("/api/v1/vendor/profile", headers=headers)

    assert response.status_code == 403


def test_vendor_profile_returns_profile_details(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)

    response = client.get("/api/v1/vendor/profile", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["business_name"] == vendor.business_name


def test_vendor_can_create_product(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()

    response = client.post(
        "/api/v1/vendor/products",
        json={
            "name": "Xiaomi Smart Band 9",
            "slug": "xiaomi-smart-band-9",
            "sku": "XIAOMI-BAND-9",
            "category_id": category.id,
            "brand_id": brand.id,
            "price": 8500,
            "stock_quantity": 14,
            "short_description": "Fitness tracker",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.get_json()["item"]["vendor"]["id"] == vendor.id


def test_vendor_create_product_rejects_duplicate_slug(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    existing = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name="Xiaomi Smart Band 8",
        slug="xiaomi-smart-band-8",
        sku="XIAOMI-BAND-8",
        price=7500,
        stock_quantity=5,
    )
    db.session.add(existing)
    db.session.commit()

    response = client.post(
        "/api/v1/vendor/products",
        json={
            "name": "Another Xiaomi Band",
            "slug": "xiaomi-smart-band-8",
            "sku": "XIAOMI-BAND-8-PRO",
            "category_id": category.id,
            "brand_id": brand.id,
            "price": 9100,
            "stock_quantity": 9,
            "short_description": "Duplicate slug test",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["slug"] == "A product with that slug already exists."


def test_vendor_can_list_owned_products(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Watch 2",
        slug="xiaomi-watch-2",
        sku="XIAOMI-WATCH-2",
        price=23000,
        stock_quantity=3,
    )

    response = client.get("/api/v1/vendor/products", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "xiaomi-watch-2"


def test_vendor_can_update_owned_product_stock(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Buds 5",
        slug="xiaomi-buds-5",
        sku="XIAOMI-BUDS-5",
        price=12000,
        stock_quantity=8,
    )

    response = client.patch(
        f"/api/v1/vendor/products/{product.id}/stock",
        json={"stock_quantity": 21},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["stock_quantity"] == 21


def test_vendor_orders_only_include_vendor_products(client):
    customer_headers = register_customer_headers(client)
    customer = User.query.filter_by(email="customer-vendor-test@example.com").first()
    address = create_address_for_user(
        customer,
        recipient_name="Customer User",
        phone_number="+254766000111",
        address_line_1="Tom Mboya Street",
    )

    vendor_headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Router AX3000",
        slug="xiaomi-router-ax3000",
        sku="XIAOMI-AX3000",
        price=15000,
        stock_quantity=6,
    )

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

    response = client.get("/api/v1/vendor/orders", headers=vendor_headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["items"][0]["product_slug"] == "xiaomi-router-ax3000"
