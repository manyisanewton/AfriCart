from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-slice@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Slice",
            "phone_number": "+254777000111",
        },
    )
    user = User.query.filter_by(email="admin-slice@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "plain-user@example.com",
            "password": "SecurePass123",
            "first_name": "Plain",
            "last_name": "User",
            "phone_number": "+254777000222",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_vendor_fixture():
    vendor_user = User(
        email="admin-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Admin",
        phone_number="+254777000333",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Admin Vendor",
        slug="admin-vendor",
        phone_number="+254777000333",
        support_email="support@adminvendor.com",
        status=VendorStatus.PENDING,
        is_verified=False,
    )
    db.session.add_all([vendor_user, vendor])
    db.session.commit()
    return vendor_user, vendor


def create_product_fixture(vendor):
    category = Category(name="Networking", slug="networking")
    brand = Brand(name="TP-Link", slug="tp-link")
    product = Product(
        vendor_id=vendor.id,
        category=category,
        brand=brand,
        name="TP-Link Archer AX55",
        slug="tp-link-archer-ax55",
        sku="TPLINK-AX55",
        price=16500,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([category, brand, product])
    db.session.commit()
    return product


def create_order_fixture(client):
    customer_headers = create_customer_headers(client)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Plain User",
        phone_number="+254777000222",
        country="Kenya",
        city="Nairobi",
        address_line_1="Ronald Ngala Street",
        is_default=True,
    )
    db.session.add(address)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
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
    return order_response.get_json()["item"]


def test_non_admin_cannot_access_admin_users(client):
    headers = create_customer_headers(client)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 403


def test_admin_can_list_users(client):
    headers = create_admin_headers(client)
    create_customer_headers(client)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    assert len(response.get_json()["items"]) >= 2


def test_admin_can_update_user_role(client):
    headers = create_admin_headers(client)
    create_customer_headers(client)
    user = User.query.filter_by(email="plain-user@example.com").first()

    response = client.patch(
        f"/api/v1/admin/users/{user.id}/role",
        json={"role": "vendor"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["role"] == "vendor"


def test_admin_can_approve_vendor(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()

    response = client.patch(
        f"/api/v1/admin/vendors/{vendor.id}/status",
        json={"status": "approved"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "approved"
    assert response.get_json()["item"]["is_verified"] is True


def test_admin_can_create_category_and_brand(client):
    headers = create_admin_headers(client)

    category_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Storage", "slug": "storage"},
        headers=headers,
    )
    brand_response = client.post(
        "/api/v1/admin/brands",
        json={"name": "SanDisk", "slug": "sandisk"},
        headers=headers,
    )

    assert category_response.status_code == 201
    assert brand_response.status_code == 201


def test_admin_can_deactivate_product(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    response = client.patch(
        f"/api/v1/admin/products/{product.id}/active",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["is_active"] is False


def test_admin_can_update_order_status(client):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)

    response = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "processing"
