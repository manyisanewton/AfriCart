from app.extensions import db
from app.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.utils.security import hash_password


def seed_catalog():
    user = User(
        email="vendor-catalog@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Owner",
        phone_number="+254711000111",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=user,
        business_name="Catalog Tech",
        slug="catalog-tech",
        phone_number="+254711000111",
        support_email="support@catalogtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    smartphones = Category(name="Smartphones", slug="smartphones")
    laptops = Category(name="Laptops", slug="laptops")
    samsung = Brand(name="Samsung", slug="samsung")
    apple = Brand(name="Apple", slug="apple")

    galaxy = Product(
        vendor=vendor,
        category=smartphones,
        brand=samsung,
        name="Samsung Galaxy S24",
        slug="samsung-galaxy-s24",
        sku="GALAXY-S24",
        short_description="Flagship Samsung smartphone",
        description="A fast flagship phone for everyday use.",
        price=99999.00,
        compare_at_price=109999.00,
        stock_quantity=12,
        is_featured=True,
    )
    macbook = Product(
        vendor=vendor,
        category=laptops,
        brand=apple,
        name="MacBook Air M3",
        slug="macbook-air-m3",
        sku="MBA-M3",
        short_description="Thin and light laptop",
        description="A lightweight laptop with long battery life.",
        price=154999.00,
        stock_quantity=7,
        is_featured=False,
    )

    db.session.add_all([user, vendor, smartphones, laptops, samsung, apple, galaxy, macbook])
    db.session.flush()

    db.session.add_all(
        [
            ProductImage(
                product=galaxy,
                image_url="https://example.com/galaxy-front.jpg",
                alt_text="Samsung Galaxy front view",
                is_primary=True,
                sort_order=0,
            ),
            ProductVariant(
                product=galaxy,
                name="256GB / Black",
                sku="GALAXY-S24-256-BLK",
                price=99999.00,
                stock_quantity=5,
                attribute_summary="256GB, Black",
            ),
        ]
    )
    db.session.commit()


def test_list_categories_returns_active_categories(client):
    seed_catalog()

    response = client.get("/api/v1/categories")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert [item["slug"] for item in items] == ["laptops", "smartphones"]


def test_list_products_returns_paginated_items(client):
    seed_catalog()

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["pagination"]["total"] == 2
    assert len(payload["items"]) == 2


def test_list_products_filters_by_category(client):
    seed_catalog()

    response = client.get("/api/v1/products?category=smartphones")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "samsung-galaxy-s24"


def test_list_products_filters_by_brand(client):
    seed_catalog()

    response = client.get("/api/v1/products?brand=apple")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "macbook-air-m3"


def test_get_product_returns_detail_view(client):
    seed_catalog()

    response = client.get("/api/v1/products/samsung-galaxy-s24")

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["slug"] == "samsung-galaxy-s24"
    assert item["primary_image"]["image_url"] == "https://example.com/galaxy-front.jpg"
    assert len(item["variants"]) == 1


def test_get_product_returns_not_found_for_unknown_slug(client):
    response = client.get("/api/v1/products/unknown-product")

    assert response.status_code == 404
    assert response.get_json()["error"]["message"] == "Product not found."
