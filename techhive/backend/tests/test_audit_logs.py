from app.models import AuditLog
from tests.factories import (
    create_address_for_user,
    create_admin_headers,
    create_catalog_dependencies,
    create_customer_headers,
    create_product,
    create_vendor_user_and_headers,
)
from app.models import User


def test_admin_category_creation_writes_audit_log(client):
    headers = create_admin_headers(client)

    response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Gaming", "slug": "gaming"},
        headers=headers,
    )

    assert response.status_code == 201

    audit_log = AuditLog.query.filter_by(action="admin.category_created").first()
    assert audit_log is not None
    assert audit_log.entity_type == "category"
    assert audit_log.metadata_json["slug"] == "gaming"


def test_admin_can_list_audit_logs(client):
    headers = create_admin_headers(client)
    client.post(
        "/api/v1/admin/categories",
        json={"name": "Office", "slug": "office"},
        headers=headers,
    )

    response = client.get("/api/v1/admin/audit-logs", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["results"]) >= 1
    assert payload["pagination"]["total"] >= 1


def test_admin_can_view_filtered_audit_log_detail(client):
    headers = create_admin_headers(client)
    client.post(
        "/api/v1/admin/categories",
        json={"name": "Office", "slug": "office"},
        headers=headers,
    )

    list_response = client.get("/api/v1/admin/audit-logs?event_type=category_created", headers=headers)

    assert list_response.status_code == 200
    item = list_response.get_json()["results"][0]
    assert item["event_type"] == "admin.category_created"

    detail_response = client.get(f"/api/v1/admin/audit-logs/{item['id']}", headers=headers)

    assert detail_response.status_code == 200
    assert detail_response.get_json()["audit_log"]["id"] == item["id"]


def test_vendor_actions_write_audit_logs(client):
    headers, vendor = create_vendor_user_and_headers(
        client,
        email="vendor-slice@example.com",
        first_name="Vendor",
        last_name="Slice",
        phone_number="+254766000222",
        business_name="Slice Vendor",
        slug="slice-vendor",
        support_email="support@vendor-slice.com",
    )
    category, brand = create_catalog_dependencies()

    create_response = client.post(
        "/api/v1/vendor/products",
        json={
            "name": "Redmi Watch 5",
            "slug": "redmi-watch-5",
            "sku": "REDMI-WATCH-5",
            "category_id": category.id,
            "brand_id": brand.id,
            "price": 13500,
            "stock_quantity": 10,
            "short_description": "Smart watch",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    product_id = create_response.get_json()["item"]["id"]

    stock_response = client.patch(
        f"/api/v1/vendor/products/{product_id}/stock",
        json={"stock_quantity": 18},
        headers=headers,
    )
    assert stock_response.status_code == 200

    audit_logs = (
        AuditLog.query.filter_by(actor_user_id=vendor.user_id)
        .order_by(AuditLog.id.asc())
        .all()
    )
    actions = [audit_log.action for audit_log in audit_logs]

    assert "vendor.product_created" in actions
    assert "vendor.product_stock_updated" in actions


def test_storefront_customer_actions_write_audit_logs(client):
    customer_headers = create_customer_headers(
        client,
        email="customer-audit@example.com",
        first_name="Customer",
        last_name="Audit",
        phone_number="+254766009999",
    )
    _vendor_headers, vendor = create_vendor_user_and_headers(
        client,
        email="vendor-audit@example.com",
        first_name="Vendor",
        last_name="Audit",
        phone_number="+254766008888",
        business_name="Audit Vendor",
        slug="audit-vendor",
        support_email="support@auditvendor.com",
    )
    category, brand = create_catalog_dependencies(
        category_name="Audio",
        category_slug="audio-audit",
        brand_name="Sony",
        brand_slug="sony-audit",
    )
    product = create_product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Sony WH-1000XM",
        slug="sony-wh-1000xm-audit",
        sku="SONY-AUD-1000",
        price=12000,
        stock_quantity=5,
        short_description="Audit headphones",
    )
    user = User.query.filter_by(email="customer-audit@example.com").first()
    address = create_address_for_user(user)

    add_cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=customer_headers,
    )
    assert add_cart_response.status_code == 201

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

    audit_logs = (
        AuditLog.query.filter_by(actor_user_id=user.id)
        .order_by(AuditLog.id.asc())
        .all()
    )
    actions = [audit_log.action for audit_log in audit_logs]

    assert "customer.account_registered" in actions
    assert "customer.cart_item_added" in actions
    assert "customer.order_created" in actions
    assert "customer.payment_created" in actions
