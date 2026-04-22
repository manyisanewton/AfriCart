from datetime import datetime, timedelta, timezone

from tests.test_admin import create_admin_headers
from tests.test_products import seed_catalog


def test_public_banners_only_return_active_items(client):
    headers = create_admin_headers(client)

    client.post(
        "/api/v1/admin/banners",
        json={
            "title": "Mid-Year Deals",
            "image_url": "https://example.com/banner-1.jpg",
            "placement": "homepage",
            "sort_order": 1,
            "is_active": True,
        },
        headers=headers,
    )
    client.post(
        "/api/v1/admin/banners",
        json={
            "title": "Hidden Banner",
            "image_url": "https://example.com/banner-2.jpg",
            "placement": "homepage",
            "sort_order": 2,
            "is_active": False,
        },
        headers=headers,
    )

    response = client.get("/api/v1/banners")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Mid-Year Deals"


def test_admin_can_create_and_list_flash_sales(client):
    headers = create_admin_headers(client)
    seed_catalog()
    now = datetime.now(timezone.utc)

    product_response = client.get("/api/v1/products")
    product_id = product_response.get_json()["items"][0]["id"]

    create_response = client.post(
        "/api/v1/admin/flash-sales",
        json={
            "title": "Weekend Rush",
            "product_id": product_id,
            "sale_price": 89999,
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=2)).isoformat(),
            "is_active": True,
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    list_response = client.get("/api/v1/admin/flash-sales", headers=headers)

    assert list_response.status_code == 200
    items = list_response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Weekend Rush"


def test_public_flash_sales_return_only_current_active_sales(client):
    headers = create_admin_headers(client)
    seed_catalog()
    now = datetime.now(timezone.utc)

    product_response = client.get("/api/v1/products")
    items = product_response.get_json()["items"]
    active_product_id = items[0]["id"]
    second_product_id = items[1]["id"]

    client.post(
        "/api/v1/admin/flash-sales",
        json={
            "title": "Today Only",
            "product_id": active_product_id,
            "sale_price": 87999,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=5)).isoformat(),
            "is_active": True,
        },
        headers=headers,
    )
    client.post(
        "/api/v1/admin/flash-sales",
        json={
            "title": "Expired Deal",
            "product_id": second_product_id,
            "sale_price": 120000,
            "starts_at": (now - timedelta(days=3)).isoformat(),
            "ends_at": (now - timedelta(days=1)).isoformat(),
            "is_active": True,
        },
        headers=headers,
    )

    response = client.get("/api/v1/flash-sales")

    assert response.status_code == 200
    flash_sales = response.get_json()["items"]
    assert len(flash_sales) == 1
    assert flash_sales[0]["title"] == "Today Only"
    assert flash_sales[0]["product"]["id"] == active_product_id
