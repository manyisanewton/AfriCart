import io

from app.extensions import db
from app.models import Address, Notification, NotificationType, OrderStatus, Payment, PaymentStatus, Product, ProductImage, User
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


def test_vendor_dashboard_returns_summary_with_links(client):
    customer_headers = register_customer_headers(client)
    customer = User.query.filter_by(email="customer-vendor-test@example.com").first()
    address = create_address_for_user(
        customer,
        recipient_name="Customer User",
        phone_number="+254766000111",
        address_line_1="Moi Avenue",
    )

    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    low_stock_product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Vendor Dashboard Low Stock",
        slug="vendor-dashboard-low-stock",
        sku="VENDOR-DASH-LOW",
        price=4200,
        stock_quantity=2,
    )
    healthy_stock_product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Vendor Dashboard Healthy Stock",
        slug="vendor-dashboard-healthy-stock",
        sku="VENDOR-DASH-HEALTHY",
        price=7800,
        stock_quantity=9,
    )
    db.session.add(
        Notification(
            user_id=vendor.user_id,
            type=NotificationType.ORDER_CREATED,
            title="New vendor order",
            message="A new order needs attention.",
        )
    )
    db.session.commit()

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": low_stock_product.id, "quantity": 1},
        headers=customer_headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=customer_headers,
    )
    assert order_response.status_code == 201
    order_id = order_response.get_json()["item"]["id"]
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "manual"},
        headers=customer_headers,
    )
    assert payment_response.status_code in (200, 201)
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.status = PaymentStatus.PAID
    db.session.commit()

    response = client.get("/api/v1/vendor/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()["item"]
    assert payload["persona"] == "vendor"
    assert payload["generated_at"]
    assert payload["summary"]["business_name"] == vendor.business_name
    assert payload["summary"]["product_count"] == 2
    assert payload["summary"]["low_stock_count"] == 1
    assert payload["summary"]["links"]["products"] == "/api/v1/vendor/products"
    assert payload["sales"]["meta"]["limit"] == 5
    assert payload["sales"]["total_orders"] >= 1
    assert payload["sales"]["top_products"][0]["links"]["product"] == f"/api/v1/vendor/products/{low_stock_product.id}"
    assert payload["inventory"]["meta"]["total_count"] == 1
    assert payload["inventory"]["low_stock_items"][0]["slug"] == "vendor-dashboard-low-stock"
    assert payload["inventory"]["low_stock_items"][0]["links"]["product"] == (
        f"/api/v1/vendor/products/{low_stock_product.id}"
    )
    assert payload["orders"]["recent"][0]["links"]["orders"] == "/api/v1/vendor/orders"
    assert payload["notifications"]["unread_count"] >= 1
    assert payload["notifications"]["meta"]["returned_count"] >= 1
    assert payload["notifications"]["latest"][0]["links"]["notifications"] == "/api/v1/notifications"


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


def test_vendor_can_bulk_import_and_export_products(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()

    import_response = client.post(
        "/api/v1/vendor/products/bulk-import",
        json={
            "items": [
                {
                    "name": "Bulk Router One",
                    "slug": "bulk-router-one",
                    "sku": "BULK-ROUTER-ONE",
                    "category_id": category.id,
                    "brand_id": brand.id,
                    "price": 12000,
                    "stock_quantity": 8,
                },
                {
                    "name": "Bulk Router Two",
                    "slug": "bulk-router-two",
                    "sku": "BULK-ROUTER-TWO",
                    "category_id": category.id,
                    "brand_id": brand.id,
                    "price": 18000,
                    "stock_quantity": 4,
                    "is_featured": True,
                },
            ]
        },
        headers=headers,
    )

    assert import_response.status_code == 200
    assert import_response.get_json()["created_count"] == 2

    export_response = client.get("/api/v1/vendor/products/export", headers=headers)

    assert export_response.status_code == 200
    payload = export_response.get_json()
    assert payload["summary"]["product_count"] == 2
    assert {item["slug"] for item in payload["items"]} == {"bulk-router-one", "bulk-router-two"}


def test_vendor_bulk_import_can_update_existing_products(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Update Me",
        slug="update-me",
        sku="UPDATE-ME",
        price=5000,
        stock_quantity=3,
    )

    response = client.post(
        "/api/v1/vendor/products/bulk-import",
        json={
            "update_existing": True,
            "items": [
                {
                    "name": "Updated Product",
                    "slug": "update-me",
                    "sku": "UPDATE-ME",
                    "category_id": category.id,
                    "brand_id": brand.id,
                    "price": 9500,
                    "stock_quantity": 10,
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["updated_count"] == 1
    assert response.get_json()["items"][0]["price"] == "9500.00"


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


def test_vendor_can_get_owned_product_detail(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Band Pro",
        slug="xiaomi-band-pro",
        sku="XIAOMI-BAND-PRO",
        price=11000,
        stock_quantity=7,
    )

    response = client.get(f"/api/v1/vendor/products/{product.id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["slug"] == "xiaomi-band-pro"


def test_vendor_can_update_owned_product_details(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Pad 6",
        slug="xiaomi-pad-6",
        sku="XIAOMI-PAD-6",
        price=54000,
        stock_quantity=4,
        short_description="Tablet",
    )

    response = client.patch(
        f"/api/v1/vendor/products/{product.id}",
        json={
            "name": "Xiaomi Pad 6 Pro",
            "slug": "xiaomi-pad-6-pro",
            "sku": "XIAOMI-PAD-6-PRO",
            "price": 62000,
            "is_featured": True,
        },
        headers=headers,
    )

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["name"] == "Xiaomi Pad 6 Pro"
    assert item["slug"] == "xiaomi-pad-6-pro"
    assert item["sku"] == "XIAOMI-PAD-6-PRO"
    assert item["price"] == "62000.00"
    assert item["is_featured"] is True


def test_vendor_update_rejects_duplicate_sku(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    first_product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Router Mini",
        slug="xiaomi-router-mini",
        sku="XIAOMI-ROUTER-MINI",
        price=7000,
        stock_quantity=5,
    )
    second_product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Router Max",
        slug="xiaomi-router-max",
        sku="XIAOMI-ROUTER-MAX",
        price=15000,
        stock_quantity=2,
    )

    response = client.patch(
        f"/api/v1/vendor/products/{second_product.id}",
        json={"sku": first_product.sku},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["sku"] == "A product with that SKU already exists."


def test_vendor_can_delete_product_without_order_history(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Hub",
        slug="xiaomi-hub",
        sku="XIAOMI-HUB",
        price=9000,
        stock_quantity=6,
    )

    response = client.delete(f"/api/v1/vendor/products/{product.id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["message"] == "Product deleted successfully."
    assert db.session.get(Product, product.id) is None


def test_vendor_delete_rejects_product_with_order_history(client):
    customer_headers = register_customer_headers(client)
    vendor_headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Router AX1500",
        slug="xiaomi-router-ax1500",
        sku="XIAOMI-AX1500",
        price=16000,
        stock_quantity=6,
    )
    customer = User.query.filter_by(email="customer-vendor-test@example.com").first()
    address = create_address_for_user(
        customer,
        recipient_name="Customer User",
        phone_number="+254766000111",
        address_line_1="Tom Mboya Street",
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

    response = client.delete(f"/api/v1/vendor/products/{product.id}", headers=vendor_headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["product"] == (
        "Products that are part of existing orders cannot be deleted."
    )


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


def test_vendor_analytics_report_and_payout_summary(client):
    customer_headers = register_customer_headers(client)
    customer = User.query.filter_by(email="customer-vendor-test@example.com").first()
    address = create_address_for_user(
        customer,
        recipient_name="Customer User",
        phone_number="+254766000111",
        address_line_1="Tom Mboya Street",
    )

    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Analytics Router",
        slug="analytics-router",
        sku="ANALYTICS-ROUTER",
        price=20000,
        stock_quantity=2,
    )

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
    order_id = order_response.get_json()["item"]["id"]
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "manual"},
        headers=customer_headers,
    )
    assert payment_response.status_code in (200, 201)
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.status = PaymentStatus.PAID
    order = payment.order
    order.status = OrderStatus.DELIVERED
    db.session.commit()

    analytics_response = client.get("/api/v1/vendor/analytics/report", headers=headers)
    payout_response = client.get("/api/v1/vendor/payouts/summary", headers=headers)

    assert analytics_response.status_code == 200
    analytics = analytics_response.get_json()["item"]
    assert analytics["summary"]["product_count"] == 1
    assert analytics["order_status_breakdown"]["delivered"] >= 1
    assert analytics["payment_status_breakdown"]["paid"] >= 1

    assert payout_response.status_code == 200
    payout = payout_response.get_json()["item"]
    assert payout["gross_revenue"] == "40000.00"
    assert payout["ready_for_payout"] == "40000.00"
    assert payout["eligible_order_count"] == 1


def test_vendor_can_upload_product_image(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Camera Hub",
        slug="xiaomi-camera-hub",
        sku="XIAOMI-CAMERA-HUB",
        price=19500,
        stock_quantity=4,
    )

    response = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={
            "file": (io.BytesIO(b"fake-image-bytes"), "camera.jpg"),
            "alt_text": "Front view",
            "is_primary": "true",
            "sort_order": "0",
        },
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["image_url"].startswith("/media/products/")
    assert item["is_primary"] is True

    detail_response = client.get(f"/api/v1/vendor/products/{product.id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.get_json()["item"]["primary_image"]["image_url"] == item["image_url"]


def test_vendor_upload_product_image_rejects_invalid_extension(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Soundbar",
        slug="xiaomi-soundbar",
        sku="XIAOMI-SOUNDBAR",
        price=8900,
        stock_quantity=4,
    )

    response = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={"file": (io.BytesIO(b"not-an-image"), "payload.exe")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.get_json()["error"]["details"]["file"]


def test_vendor_can_delete_product_image(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Home Display",
        slug="xiaomi-home-display",
        sku="XIAOMI-HOME-DISPLAY",
        price=25500,
        stock_quantity=3,
    )
    first_upload = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={
            "file": (io.BytesIO(b"first-image"), "display.jpg"),
            "is_primary": "true",
            "sort_order": "0",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    second_upload = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={
            "file": (io.BytesIO(b"second-image"), "display-side.jpg"),
            "is_primary": "false",
            "sort_order": "1",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    first_image_id = first_upload.get_json()["item"]["id"]
    second_image_url = second_upload.get_json()["item"]["image_url"]

    response = client.delete(
        f"/api/v1/vendor/products/{product.id}/images/{first_image_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert ProductImage.query.filter_by(id=first_image_id).first() is None
    detail_response = client.get(f"/api/v1/vendor/products/{product.id}", headers=headers)
    assert detail_response.get_json()["item"]["primary_image"]["image_url"] == second_image_url


def test_vendor_can_upload_kyc_document(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)

    response = client.post(
        "/api/v1/vendor/kyc/document",
        data={"file": (io.BytesIO(b"fake-pdf-content"), "kyc.pdf")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["url"].startswith("/media/vendor-kyc/")


def test_vendor_can_create_update_and_delete_product_variant(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Smart TV",
        slug="xiaomi-smart-tv",
        sku="XIAOMI-SMART-TV",
        price=68000,
        stock_quantity=5,
    )

    create_response = client.post(
        f"/api/v1/vendor/products/{product.id}/variants",
        json={
            "name": "55 inch / Black",
            "sku": "XIAOMI-TV-55-BLK",
            "price": 68000,
            "stock_quantity": 3,
            "attribute_summary": "55 inch, Black",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    variant_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/vendor/products/{product.id}/variants/{variant_id}",
        json={"price": 69999, "stock_quantity": 2},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["price"] == "69999.00"
    assert update_response.get_json()["item"]["stock_quantity"] == 2

    list_response = client.get(f"/api/v1/vendor/products/{product.id}/variants", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    delete_response = client.delete(
        f"/api/v1/vendor/products/{product.id}/variants/{variant_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Product variant deleted successfully."


def test_vendor_variant_rejects_duplicate_sku(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Gaming Monitor",
        slug="xiaomi-gaming-monitor",
        sku="XIAOMI-GAMING-MONITOR",
        price=34000,
        stock_quantity=5,
    )

    first_response = client.post(
        f"/api/v1/vendor/products/{product.id}/variants",
        json={
            "name": "27 inch",
            "sku": "XIAOMI-MONITOR-27",
            "price": 34000,
            "stock_quantity": 3,
        },
        headers=headers,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        f"/api/v1/vendor/products/{product.id}/variants",
        json={
            "name": "32 inch",
            "sku": "XIAOMI-MONITOR-27",
            "price": 42000,
            "stock_quantity": 2,
        },
        headers=headers,
    )
    assert second_response.status_code == 400
    assert second_response.get_json()["error"]["details"]["sku"] == "A variant with that SKU already exists."


def test_vendor_can_update_product_image_metadata(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Wall Light",
        slug="xiaomi-wall-light",
        sku="XIAOMI-WALL-LIGHT",
        price=4500,
        stock_quantity=8,
    )
    first_upload = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={
            "file": (io.BytesIO(b"first"), "light-front.jpg"),
            "is_primary": "true",
            "sort_order": "0",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    second_upload = client.post(
        f"/api/v1/vendor/products/{product.id}/images",
        data={
            "file": (io.BytesIO(b"second"), "light-side.jpg"),
            "is_primary": "false",
            "sort_order": "1",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    second_image_id = second_upload.get_json()["item"]["id"]

    response = client.patch(
        f"/api/v1/vendor/products/{product.id}/images/{second_image_id}",
        json={"alt_text": "Side profile", "is_primary": True, "sort_order": 0},
        headers=headers,
    )

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["alt_text"] == "Side profile"
    assert item["is_primary"] is True
    detail_response = client.get(f"/api/v1/vendor/products/{product.id}", headers=headers)
    assert detail_response.get_json()["item"]["primary_image"]["id"] == second_image_id


def test_vendor_can_view_low_stock_products(client):
    headers, vendor = create_vendor_user_and_headers_wrapper(client)
    category, brand = create_catalog_dependencies()
    low_stock_product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Mini PC",
        slug="xiaomi-mini-pc",
        sku="XIAOMI-MINI-PC",
        price=72000,
        stock_quantity=2,
    )
    create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Xiaomi Tower Fan",
        slug="xiaomi-tower-fan",
        sku="XIAOMI-TOWER-FAN",
        price=13500,
        stock_quantity=9,
    )

    response = client.get("/api/v1/vendor/inventory/low-stock?threshold=3", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["threshold"] == 3
    assert payload["summary"]["count"] == 1
    assert payload["items"][0]["slug"] == low_stock_product.slug
