from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "promo-admin@example.com",
            "password": "SecurePass123",
            "first_name": "Promo",
            "last_name": "Admin",
            "phone_number": "+254711111001",
        },
    )
    user = User.query.filter_by(email="promo-admin@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "promo-customer@example.com",
            "password": "SecurePass123",
            "first_name": "Promo",
            "last_name": "Customer",
            "phone_number": "+254711111002",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product():
    vendor_user = User(
        email="promo-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Promo",
        last_name="Vendor",
        phone_number="+254711111003",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Promo Tech",
        slug="promo-tech",
        phone_number="+254711111003",
        support_email="support@promotech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Keyboards", slug="keyboards")
    brand = Brand(name="Logitech", slug="logitech")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Logitech MX Keys S",
        slug="logitech-mx-keys-s",
        sku="LOGI-MX-KEYS-S",
        price=15000.00,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_address():
    user = User.query.filter_by(email="promo-customer@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Promo Customer",
        phone_number="+254711111002",
        country="Kenya",
        city="Nairobi",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def test_admin_can_create_promo_code(client):
    admin_headers = create_admin_headers(client)

    response = client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
            "minimum_order_amount": 1000,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.get_json()["item"]["code"] == "SAVE10"


def test_customer_can_preview_cart_promo(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    product = create_product()
    client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
            "minimum_order_amount": 1000,
        },
        headers=admin_headers,
    )
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=customer_headers,
    )
    assert cart_response.status_code == 201

    response = client.post(
        "/api/v1/cart/apply-promo",
        json={"promo_code": "SAVE10"},
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["discount_amount"] == "3000.00"


def test_order_applies_discounted_total(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    product = create_product()
    address = create_address()
    client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
            "minimum_order_amount": 1000,
        },
        headers=admin_headers,
    )
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=customer_headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id, "promo_code": "SAVE10"},
        headers=customer_headers,
    )

    assert order_response.status_code == 201
    item = order_response.get_json()["item"]
    assert item["promo_code"] == "SAVE10"
    assert item["discount_amount"] == "3000.00"
