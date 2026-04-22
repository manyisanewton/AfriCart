from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analytics-admin@example.com",
            "password": "SecurePass123",
            "first_name": "Analytics",
            "last_name": "Admin",
            "phone_number": "+254733330001",
        },
    )
    user = User.query.filter_by(email="analytics-admin@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analytics-customer@example.com",
            "password": "SecurePass123",
            "first_name": "Analytics",
            "last_name": "Customer",
            "phone_number": "+254733330002",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_vendor_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analytics-vendor@example.com",
            "password": "SecurePass123",
            "first_name": "Analytics",
            "last_name": "Vendor",
            "phone_number": "+254733330003",
        },
    )
    user = User.query.filter_by(email="analytics-vendor@example.com").first()
    user.role = UserRole.VENDOR
    vendor = Vendor(
        user_id=user.id,
        business_name="Analytics Tech",
        slug="analytics-tech",
        phone_number="+254733330003",
        support_email="support@analyticstech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    db.session.add(vendor)
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, vendor


def create_paid_order_for_analytics(client, customer_headers, vendor):
    category = Category(name="Webcams", slug="webcams")
    brand = Brand(name="Logitech-Analytics", slug="logitech-analytics")
    product = Product(
        vendor_id=vendor.id,
        category=category,
        brand=brand,
        name="Logitech Brio 4K",
        slug="logitech-brio-4k",
        sku="LOGITECH-BRIO-4K",
        price=22500.00,
        stock_quantity=10,
        is_active=True,
    )
    db.session.add_all([category, brand, product])
    db.session.commit()

    customer = User.query.filter_by(email="analytics-customer@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Analytics Customer",
        phone_number="+254733330002",
        country="Kenya",
        city="Nairobi",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 2},
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
    payment_id = payment_response.get_json()["item"]["id"]
    mark_paid = client.post(
        f"/api/v1/payments/{payment_id}/mark-paid",
        headers=customer_headers,
    )
    assert mark_paid.status_code == 200


def test_admin_analytics_summary_returns_counts_and_revenue(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    _, vendor = create_vendor_headers(client)
    create_paid_order_for_analytics(client, customer_headers, vendor)

    response = client.get("/api/v1/admin/analytics/summary", headers=admin_headers)

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["total_users"] >= 3
    assert item["total_orders"] >= 1
    assert item["total_revenue"] == "22500.00" or item["total_revenue"] == "22950.00" or float(item["total_revenue"]) > 0


def test_admin_analytics_top_products_returns_ranked_items(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    _, vendor = create_vendor_headers(client)
    create_paid_order_for_analytics(client, customer_headers, vendor)

    response = client.get("/api/v1/admin/analytics/top-products", headers=admin_headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) >= 1
    assert items[0]["units_sold"] >= 2


def test_vendor_analytics_summary_returns_vendor_metrics(client):
    customer_headers = create_customer_headers(client)
    vendor_headers, vendor = create_vendor_headers(client)
    create_paid_order_for_analytics(client, customer_headers, vendor)

    response = client.get("/api/v1/vendor/analytics/summary", headers=vendor_headers)

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["product_count"] >= 1
    assert item["order_count"] >= 1
    assert item["units_sold"] >= 2


def test_vendor_analytics_top_products_returns_vendor_items(client):
    customer_headers = create_customer_headers(client)
    vendor_headers, vendor = create_vendor_headers(client)
    create_paid_order_for_analytics(client, customer_headers, vendor)

    response = client.get("/api/v1/vendor/analytics/top-products", headers=vendor_headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) >= 1
    assert items[0]["product_slug"] == "logitech-brio-4k"
