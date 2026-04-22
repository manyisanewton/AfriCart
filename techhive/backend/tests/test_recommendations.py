from app.extensions import db
from app.models import Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "recommend-user@example.com",
            "password": "SecurePass123",
            "first_name": "Recommend",
            "last_name": "User",
            "phone_number": "+254799000111",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_recommendation_catalog():
    vendor_user = User(
        email="recommend-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Signals",
        phone_number="+254799000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Tech",
        slug="recommendation-tech",
        phone_number="+254799000222",
        support_email="support@recommendationtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    phones = Category(name="Phones", slug="phones")
    accessories = Category(name="Accessories", slug="accessories")
    samsung = Brand(name="Samsung", slug="samsung-rec")
    anker = Brand(name="Anker", slug="anker-rec")

    seed_phone = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Samsung Galaxy Seed",
        slug="samsung-galaxy-seed",
        sku="SAMSUNG-SEED",
        price=60000,
        stock_quantity=4,
        is_featured=False,
    )
    recommended_phone = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Samsung Galaxy Match",
        slug="samsung-galaxy-match",
        sku="SAMSUNG-MATCH",
        price=70000,
        stock_quantity=6,
        is_featured=True,
    )
    fallback_product = Product(
        vendor=vendor,
        category=accessories,
        brand=anker,
        name="Anker Charger Pro",
        slug="anker-charger-pro",
        sku="ANKER-PRO",
        price=4500,
        stock_quantity=10,
        is_featured=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            phones,
            accessories,
            samsung,
            anker,
            seed_phone,
            recommended_phone,
            fallback_product,
        ]
    )
    db.session.commit()
    return seed_phone, recommended_phone, fallback_product


def test_recommendations_fallback_for_new_user(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 3
    assert items[0]["slug"] in {recommended_phone.slug, fallback_product.slug}


def test_recommendations_use_user_signals_and_exclude_seed_product(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    add_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": seed_phone.id},
        headers=headers,
    )
    assert add_response.status_code == 201

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == recommended_phone.slug
    assert all(item["slug"] != seed_phone.slug for item in items)
