from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def register_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer-vendor-test@example.com",
            "password": "SecurePass123",
            "first_name": "Customer",
            "last_name": "User",
            "phone_number": "+254766000111",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_vendor_user_and_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "vendor-slice@example.com",
            "password": "SecurePass123",
            "first_name": "Vendor",
            "last_name": "Slice",
            "phone_number": "+254766000222",
        },
    )
    user = User.query.filter_by(email="vendor-slice@example.com").first()
    user.role = UserRole.VENDOR
    vendor = Vendor(
        user_id=user.id,
        business_name="Slice Vendor",
        slug="slice-vendor",
        phone_number="+254766000222",
        support_email="support@vendor-slice.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    db.session.add(vendor)
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, vendor


def create_catalog_dependencies():
    category = Category(name="Wearables", slug="wearables")
    brand = Brand(name="Xiaomi", slug="xiaomi")
    db.session.add_all([category, brand])
    db.session.commit()
    return category, brand


def test_customer_cannot_access_vendor_profile(client):
    headers = register_customer_headers(client)

    response = client.get("/api/v1/vendor/profile", headers=headers)

    assert response.status_code == 403


def test_vendor_profile_returns_profile_details(client):
    headers, vendor = create_vendor_user_and_headers(client)

    response = client.get("/api/v1/vendor/profile", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["business_name"] == vendor.business_name


def test_vendor_can_create_product(client):
    headers, vendor = create_vendor_user_and_headers(client)
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


def test_vendor_can_list_owned_products(client):
    headers, vendor = create_vendor_user_and_headers(client)
    category, brand = create_catalog_dependencies()
    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name="Xiaomi Watch 2",
        slug="xiaomi-watch-2",
        sku="XIAOMI-WATCH-2",
        price=23000,
        stock_quantity=3,
    )
    db.session.add(product)
    db.session.commit()

    response = client.get("/api/v1/vendor/products", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "xiaomi-watch-2"


def test_vendor_can_update_owned_product_stock(client):
    headers, vendor = create_vendor_user_and_headers(client)
    category, brand = create_catalog_dependencies()
    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name="Xiaomi Buds 5",
        slug="xiaomi-buds-5",
        sku="XIAOMI-BUDS-5",
        price=12000,
        stock_quantity=8,
    )
    db.session.add(product)
    db.session.commit()

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
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Customer User",
        phone_number="+254766000111",
        country="Kenya",
        city="Nairobi",
        address_line_1="Tom Mboya Street",
        is_default=True,
    )
    db.session.add(address)

    vendor_headers, vendor = create_vendor_user_and_headers(client)
    category, brand = create_catalog_dependencies()
    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name="Xiaomi Router AX3000",
        slug="xiaomi-router-ax3000",
        sku="XIAOMI-AX3000",
        price=15000,
        stock_quantity=6,
    )
    db.session.add(product)
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

    response = client.get("/api/v1/vendor/orders", headers=vendor_headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["items"][0]["product_slug"] == "xiaomi-router-ax3000"
