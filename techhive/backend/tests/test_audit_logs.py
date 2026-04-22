from app.models import AuditLog
from tests.test_admin import create_admin_headers
from tests.test_vendors import create_catalog_dependencies, create_vendor_user_and_headers


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
    assert len(response.get_json()["items"]) >= 1


def test_vendor_actions_write_audit_logs(client):
    headers, vendor = create_vendor_user_and_headers(client)
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
