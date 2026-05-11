from app.extensions import db
from app.models import Address, Brand, Category, Notification, NotificationType, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer-dashboard@example.com",
            "password": "SecurePass123",
            "first_name": "Customer",
            "last_name": "Dashboard",
            "phone_number": "+254711000111",
        },
    )
    return {"Authorization": f"Bearer {response.get_json()['tokens']['access_token']}"}


def create_vendor_and_products():
    vendor_user = User(
        email="customer-dashboard-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Dashboard",
        phone_number="+254711000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Customer Dashboard Vendor",
        slug="customer-dashboard-vendor",
        phone_number="+254711000222",
        support_email="support@customerdashvendor.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Customer Dashboard Gadgets", slug="customer-dashboard-gadgets")
    brand = Brand(name="CustomerDash", slug="customerdash")
    primary_product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Customer Signal Product",
        slug="customer-signal-product",
        sku="CUSTOMER-SIGNAL-001",
        price=5500,
        stock_quantity=4,
        is_active=True,
    )
    recommended_product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Customer Recommended Product",
        slug="customer-recommended-product",
        sku="CUSTOMER-RECOMMENDED-001",
        price=6200,
        stock_quantity=7,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, primary_product, recommended_product])
    db.session.commit()
    return primary_product, recommended_product


def test_vendor_cannot_access_customer_dashboard(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "vendor-dashboard-role@example.com",
            "password": "SecurePass123",
            "first_name": "Vendor",
            "last_name": "Role",
            "phone_number": "+254711000333",
        },
    )
    user = User.query.filter_by(email="vendor-dashboard-role@example.com").first()
    user.role = UserRole.VENDOR
    db.session.commit()
    headers = {"Authorization": f"Bearer {response.get_json()['tokens']['access_token']}"}

    dashboard_response = client.get("/api/v1/customer/dashboard", headers=headers)

    assert dashboard_response.status_code == 403


def test_customer_dashboard_returns_summary_with_links(client):
    headers = create_customer_headers(client)
    customer = User.query.filter_by(email="customer-dashboard@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Customer Dashboard",
        phone_number="+254711000111",
        country="Kenya",
        city="Nairobi",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    primary_product, recommended_product = create_vendor_and_products()
    db.session.add(
        Notification(
            user_id=customer.id,
            type=NotificationType.ADMIN_ANNOUNCEMENT,
            title="Customer alert",
            message="Your dashboard has a fresh notification.",
        )
    )
    db.session.commit()

    wishlist_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": primary_product.id, "quantity": 1},
        headers=headers,
    )
    assert wishlist_response.status_code in (200, 201)

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": primary_product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201
    order_id = order_response.get_json()["item"]["id"]

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "manual"},
        headers=headers,
    )
    assert payment_response.status_code in (200, 201)

    dashboard_response = client.get("/api/v1/customer/dashboard", headers=headers)

    assert dashboard_response.status_code == 200
    payload = dashboard_response.get_json()["item"]
    assert payload["persona"] == "customer"
    assert payload["generated_at"]
    assert payload["summary"]["order_count"] >= 1
    assert payload["summary"]["address_count"] == 1
    assert payload["summary"]["wishlist_count"] >= 1
    assert payload["summary"]["links"]["orders"] == "/api/v1/orders"
    assert payload["summary"]["links"]["addresses"] == "/api/v1/addresses"
    assert payload["orders"]["meta"]["total_count"] >= 1
    assert payload["orders"]["recent"][0]["links"]["order"] == f"/api/v1/orders/{order_id}"
    assert payload["payments"]["recent"][0]["links"]["payments"] == "/api/v1/payments"
    assert payload["addresses"]["default"]["label"] == "Home"
    assert payload["notifications"]["latest"][0]["links"]["notifications"] == "/api/v1/notifications"
    assert payload["recommendations"]["meta"]["limit"] == 6
    assert any(item["slug"] == recommended_product.slug for item in payload["recommendations"]["items"])
    assert all(item["reason_code"] for item in payload["recommendations"]["items"])
    assert all(item["reason_label"] for item in payload["recommendations"]["items"])
    assert all(
        item["links"]["recommendations"] == "/api/v1/products/recommendations"
        for item in payload["recommendations"]["items"]
    )
