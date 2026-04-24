from app.extensions import db
from app.models import Product
from tests.factories import seed_catalog


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


def test_list_products_supports_search_query(client):
    seed_catalog()

    response = client.get("/api/v1/products?q=Galaxy")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "samsung-galaxy-s24"


def test_list_products_supports_price_sorting(client):
    seed_catalog()

    response = client.get("/api/v1/products?sort=price_asc")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == "samsung-galaxy-s24"
    assert items[1]["slug"] == "macbook-air-m3"


def test_list_products_supports_price_range_filter(client):
    seed_catalog()

    response = client.get("/api/v1/products?min_price=100000&max_price=200000")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "macbook-air-m3"


def test_list_products_supports_in_stock_filter(client):
    seed_catalog()
    product = Product.query.filter_by(slug="macbook-air-m3").first()
    product.stock_quantity = 0
    db.session.commit()

    response = client.get("/api/v1/products?in_stock=true")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "samsung-galaxy-s24"


def test_product_autocomplete_returns_matching_names(client):
    seed_catalog()

    response = client.get("/api/v1/products/autocomplete?q=Mac")

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
