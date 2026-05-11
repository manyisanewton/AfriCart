from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from app.services import payment_reconciliation_service as reconciliation_service
from app.extensions import db
from app.models import (
    Address,
    AuditLog,
    Brand,
    Category,
    NotificationDelivery,
    NotificationDeliveryStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PlatformSetting,
    Product,
    RecommendationEvent,
    SupportTicket,
    SupportTicketStatus,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.utils.security import hash_password
from tests.factories import create_admin_headers as create_admin_headers_base


def create_admin_headers(client):
    return create_admin_headers_base(
        client,
        email="admin-slice@example.com",
        first_name="Admin",
        last_name="Slice",
        phone_number="+254777000111",
    )


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


def test_admin_can_manage_recommendation_settings(client):
    headers = create_admin_headers(client)

    update_response = client.patch(
        "/api/v1/admin/recommendations/settings",
        json={
            "popularity_blend_weight": 0.8,
            "max_brand_recommendations": 3,
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    items = update_response.get_json()["items"]
    values = {item["key"]: item["value"] for item in items}
    assert values["popularity_blend_weight"] == 0.8
    assert values["max_brand_recommendations"] == 3
    assert PlatformSetting.query.filter_by(
        key="recommendation.popularity_blend_weight"
    ).first() is not None


def test_admin_can_view_overview_report_and_operations_queues(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Queue Home",
        recipient_name="Plain User",
        phone_number="+254777000222",
        country="Kenya",
        city="Nairobi",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    support_ticket = SupportTicket(
        name="Ops Queue User",
        email="ops-queue@example.com",
        subject="Open queue item",
        message="Need help",
        category="general",
        status=SupportTicketStatus.OPEN,
    )
    db.session.add_all([address, support_ticket])
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
    order_id = order_response.get_json()["item"]["id"]
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "manual"},
        headers=customer_headers,
    )
    assert payment_response.status_code in (200, 201)

    overview_response = client.get("/api/v1/admin/reports/overview", headers=headers)
    queues_response = client.get("/api/v1/admin/operations/queues", headers=headers)

    assert overview_response.status_code == 200
    overview = overview_response.get_json()["item"]
    assert overview["summary"]["total_users"] >= 3
    assert "orders" in overview["breakdowns"]

    assert queues_response.status_code == 200
    queues = queues_response.get_json()["item"]
    assert queues["summary"]["pending_vendor_count"] >= 1
    assert queues["summary"]["open_support_ticket_count"] >= 1
    assert isinstance(queues["queues"]["pending_vendor_ids"], list)


def test_admin_can_view_vendor_performance_report(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Vendor Perf Home",
        recipient_name="Plain User",
        phone_number="+254777000222",
        country="Kenya",
        city="Nairobi",
        address_line_1="Kimathi Street",
        is_default=True,
    )
    db.session.add(address)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    db.session.commit()

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
    payment = db.session.get(Payment, payment_response.get_json()["item"]["id"])
    payment.status = PaymentStatus.PAID
    db.session.commit()

    response = client.get("/api/v1/admin/reports/vendors-performance?limit=5", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items
    assert items[0]["business_name"] == vendor.business_name
    assert Decimal(items[0]["revenue"]) >= Decimal("16500.00")


def test_admin_can_view_recommendation_metrics(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    db.session.add_all(
        [
            RecommendationEvent(
                user_id=customer.id,
                product_id=product.id,
                event_type="impression",
                mode="for_you",
                reason_code="similar_brand_preference",
            ),
            RecommendationEvent(
                user_id=customer.id,
                product_id=product.id,
                event_type="click",
                mode="for_you",
                reason_code="similar_brand_preference",
            ),
        ]
    )
    db.session.commit()

    response = client.get("/api/v1/admin/recommendations/metrics", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()["item"]
    assert payload["summary"]["impressions"] == 1
    assert payload["summary"]["clicks"] == 1
    assert payload["summary"]["ctr"] == 1.0
    assert payload["by_mode"][0]["mode"] == "for_you"


def test_admin_can_view_mpesa_logs(client, tmp_path):
    headers = create_admin_headers(client)
    client.application.config["MPESA_LOG_DIR"] = str(tmp_path)
    client.application.config["MPESA_LOG_FILE"] = "mpesa.log"
    log_file = Path(tmp_path) / "mpesa.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-05-08 12:30:19,925 - DEBUG - Sending STK Push request: {...}",
                "2026-05-08 12:30:41,111 - DEBUG - STK Push response received: {...}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.get("/api/v1/admin/logs/mpesa?limit=10", headers=headers)

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["exists"] is True
    assert item["line_count"] == 2
    assert "Sending STK Push request" in item["lines"][0]


def test_admin_mpesa_logs_reject_invalid_limit(client):
    headers = create_admin_headers(client)

    response = client.get("/api/v1/admin/logs/mpesa?limit=0", headers=headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["limit"] == "limit must be a positive integer."


def test_admin_dashboard_returns_summary_with_links(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    customer = User.query.filter_by(email="plain-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Office",
        recipient_name="Plain User",
        phone_number="+254777000222",
        country="Kenya",
        city="Nairobi",
        address_line_1="Kimathi Street",
        is_default=True,
    )
    db.session.add(address)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    support_ticket = SupportTicket(
        name="Ops User",
        email="ops@example.com",
        subject="Help needed",
        message="Need platform help",
        category="orders",
        status=SupportTicketStatus.OPEN,
    )
    db.session.add(support_ticket)
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
    order_id = order_response.get_json()["item"]["id"]
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "manual"},
        headers=customer_headers,
    )
    assert payment_response.status_code in (200, 201)
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.status = PaymentStatus.FAILED
    db.session.flush()

    failed_delivery = NotificationDelivery(
        user_id=customer.id,
        channel="email",
        status=NotificationDeliveryStatus.FAILED,
        recipient=customer.email,
        subject="Failed notification",
        template="admin_announcement",
        reason="smtp timeout",
    )
    db.session.add(failed_delivery)
    db.session.add(
        AuditLog(
            actor_user_id=User.query.filter_by(email="admin-slice@example.com").first().id,
            action="admin.test_event",
            entity_type="system",
            entity_id=1,
            metadata_json={"source": "test"},
        )
    )
    db.session.commit()

    response = client.get("/api/v1/admin/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()["item"]
    assert payload["persona"] == "admin"
    assert payload["generated_at"]
    assert payload["summary"]["user_count"] >= 3
    assert payload["summary"]["links"]["users"] == "/api/v1/admin/users"
    assert payload["summary"]["links"]["notification_deliveries"] == "/api/v1/admin/notification-deliveries"
    assert payload["catalog"]["product_count"] >= 1
    assert payload["catalog"]["meta"]["limit"] == 5
    assert payload["catalog"]["links"]["products"] == "/api/v1/admin/products"
    assert payload["commerce"]["recent_orders"][0]["links"]["orders"] == "/api/v1/admin/orders"
    assert payload["commerce"]["recent_payments"][0]["links"]["payments"] == "/api/v1/payments"
    assert payload["operations"]["recent_support_tickets"][0]["links"]["support_tickets"] == (
        "/api/v1/admin/support-tickets"
    )
    assert payload["operations"]["meta"]["returned_count"] >= 1
    assert payload["operations"]["failed_notification_deliveries"][0]["status"] == "failed"
    assert payload["audit"]["latest_events"][0]["links"]["audit_logs"] == "/api/v1/admin/audit-logs"


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


def test_admin_can_update_user_active_state(client):
    headers = create_admin_headers(client)
    create_customer_headers(client)
    user = User.query.filter_by(email="plain-user@example.com").first()

    response = client.patch(
        f"/api/v1/admin/users/{user.id}/active",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["is_active"] is False


def test_admin_can_create_and_update_platform_setting(client):
    headers = create_admin_headers(client)

    create_response = client.post(
        "/api/v1/admin/settings",
        json={
            "key": "storefront.hero_banner_enabled",
            "value": "true",
            "description": "Controls the homepage hero banner.",
            "is_public": True,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["item"]["key"] == "storefront.hero_banner_enabled"

    update_response = client.patch(
        "/api/v1/admin/settings/storefront.hero_banner_enabled",
        json={"value": "false", "description": "Disabled for testing."},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["value"] == "false"
    assert update_response.get_json()["item"]["description"] == "Disabled for testing."


def test_admin_can_list_support_tickets_and_update_status(client):
    headers = create_admin_headers(client)
    support_response = client.post(
        "/api/v1/support/tickets",
        json={
            "name": "Plain User",
            "email": "plain-user@example.com",
            "phone_number": "+254777000222",
            "subject": "Need order help",
            "message": "Please assist with my order.",
            "category": "orders",
        },
    )
    assert support_response.status_code == 201
    ticket_id = support_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/support-tickets", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) >= 1

    update_response = client.patch(
        f"/api/v1/admin/support-tickets/{ticket_id}/status",
        json={"status": "resolved", "admin_note": "Customer guided to tracking page."},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["status"] == "resolved"
    assert update_response.get_json()["item"]["admin_note"] == "Customer guided to tracking page."
    assert update_response.get_json()["item"]["resolved_at"] is not None


def test_admin_can_filter_support_tickets_by_status(client):
    headers = create_admin_headers(client)
    first_ticket = SupportTicket(
        name="First User",
        email="first@example.com",
        subject="Question one",
        message="Question one body",
        category="general",
    )
    second_ticket = SupportTicket(
        name="Second User",
        email="second@example.com",
        subject="Question two",
        message="Question two body",
        category="payments",
    )
    db.session.add_all([first_ticket, second_ticket])
    db.session.commit()
    second_ticket.status = SupportTicketStatus.RESOLVED
    db.session.commit()

    response = client.get("/api/v1/admin/support-tickets?status=resolved", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["email"] == "second@example.com"


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


def test_admin_can_update_and_delete_category(client):
    headers = create_admin_headers(client)
    create_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Storage", "slug": "storage"},
        headers=headers,
    )
    category_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/categories/{category_id}",
        json={"name": "Storage Devices", "is_active": False},
        headers=headers,
    )
    delete_response = client.delete(
        f"/api/v1/admin/categories/{category_id}",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["name"] == "Storage Devices"
    assert update_response.get_json()["item"]["is_active"] is False
    assert delete_response.status_code == 200


def test_admin_cannot_delete_category_with_products(client):
    headers = create_admin_headers(client)
    _vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    response = client.delete(
        f"/api/v1/admin/categories/{product.category_id}",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["category"] == (
        "Categories with products cannot be deleted."
    )


def test_admin_can_update_and_delete_brand(client):
    headers = create_admin_headers(client)
    create_response = client.post(
        "/api/v1/admin/brands",
        json={"name": "SanDisk", "slug": "sandisk"},
        headers=headers,
    )
    brand_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/brands/{brand_id}",
        json={"name": "SanDisk Pro", "website_url": "https://example.com"},
        headers=headers,
    )
    delete_response = client.delete(
        f"/api/v1/admin/brands/{brand_id}",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["name"] == "SanDisk Pro"
    assert update_response.get_json()["item"]["website_url"] == "https://example.com"
    assert delete_response.status_code == 200


def test_admin_rejects_duplicate_category_slug(client):
    headers = create_admin_headers(client)
    db.session.add(Category(name="Storage", slug="storage"))
    db.session.commit()

    response = client.post(
        "/api/v1/admin/categories",
        json={"name": "More Storage", "slug": "storage"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["slug"] == (
        "A category with that slug already exists."
    )


def test_admin_rejects_duplicate_promo_code(client):
    headers = create_admin_headers(client)
    response = client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
        },
        headers=headers,
    )
    assert response.status_code == 201

    duplicate_response = client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "fixed",
            "discount_value": 100,
        },
        headers=headers,
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.get_json()["error"]["details"]["code"] == (
        "A promo code with that code already exists."
    )


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


def test_admin_can_update_and_delete_banner(client):
    headers = create_admin_headers(client)
    create_response = client.post(
        "/api/v1/admin/banners",
        json={
            "title": "Launch Banner",
            "image_url": "https://example.com/banner.jpg",
            "placement": "homepage",
            "sort_order": 1,
        },
        headers=headers,
    )
    banner_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/banners/{banner_id}",
        json={"title": "Updated Banner", "is_active": False},
        headers=headers,
    )
    delete_response = client.delete(
        f"/api/v1/admin/banners/{banner_id}",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["title"] == "Updated Banner"
    assert update_response.get_json()["item"]["is_active"] is False
    assert delete_response.status_code == 200


def test_admin_can_update_and_delete_promo_code(client):
    headers = create_admin_headers(client)
    create_response = client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": 10,
        },
        headers=headers,
    )
    promo_code_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/promo-codes/{promo_code_id}",
        json={"code": "SAVE15", "discount_value": 15, "is_active": False},
        headers=headers,
    )
    delete_response = client.delete(
        f"/api/v1/admin/promo-codes/{promo_code_id}",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["code"] == "SAVE15"
    assert update_response.get_json()["item"]["discount_value"] == "15.00"
    assert update_response.get_json()["item"]["is_active"] is False
    assert delete_response.status_code == 200


def test_admin_can_update_and_delete_flash_sale(client):
    headers = create_admin_headers(client)
    _vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    now = datetime.now(timezone.utc)
    create_response = client.post(
        "/api/v1/admin/flash-sales",
        json={
            "title": "Weekend Rush",
            "product_id": product.id,
            "sale_price": 14999,
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=2)).isoformat(),
            "is_active": True,
        },
        headers=headers,
    )
    flash_sale_id = create_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/flash-sales/{flash_sale_id}",
        json={"title": "Weekend Rush Extended", "is_active": False},
        headers=headers,
    )
    delete_response = client.delete(
        f"/api/v1/admin/flash-sales/{flash_sale_id}",
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["title"] == "Weekend Rush Extended"
    assert update_response.get_json()["item"]["is_active"] is False
    assert delete_response.status_code == 200


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


def test_admin_rejects_invalid_order_transition(client):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)

    response = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "delivered"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_order_transition"


def test_admin_can_reconcile_stale_mpesa_payments(client):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    assert payment_response.status_code == 201
    payment_id = payment_response.get_json()["item"]["id"]

    payment = db.session.get(Payment, payment_id)
    payment.method = PaymentMethod.MPESA
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["awaiting_confirmation_count"] == 1
    assert response.get_json()["timed_out_count"] == 0
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "pending"
    assert item["failure_code"] == "awaiting_provider_confirmation"
    assert item["reconciliation_attempts"] == 1

    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    timeout_response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert timeout_response.status_code == 200
    assert timeout_response.get_json()["awaiting_confirmation_count"] == 0
    assert timeout_response.get_json()["timed_out_count"] == 1
    timed_out_item = timeout_response.get_json()["items"][0]
    assert timed_out_item["id"] == payment_id
    assert timed_out_item["status"] == "failed"
    assert timed_out_item["failure_code"] == "reconciliation_timeout"
    assert timed_out_item["reconciliation_attempts"] == 2


def test_admin_reconcile_stale_rejects_invalid_limit(client):
    admin_headers = create_admin_headers(client)

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": "invalid"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["limit"] == "limit must be a positive integer."


def test_admin_reconciliation_marks_provider_failed_payment(client, monkeypatch):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    monkeypatch.setattr(
        reconciliation_service,
        "query_mpesa_payment_status",
        lambda payment: {
            "state": "failed",
            "failure_code": "insufficient_funds",
            "failure_message": "The M-Pesa account has insufficient funds.",
            "raw": {"provider": "mpesa", "result_code": 1},
        },
    )

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["provider_failed_count"] == 1
    assert response.get_json()["manual_review_count"] == 0
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "failed"
    assert item["failure_code"] == "insufficient_funds"


def test_admin_reconciliation_marks_manual_review_when_provider_reports_success_without_callback(
    client,
    monkeypatch,
):
    admin_headers = create_admin_headers(client)
    order = create_order_fixture(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "plain-user@example.com", "password": "SecurePass123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {login_response.get_json()['tokens']['access_token']}"
    }

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254777000222"},
        headers=customer_headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]
    payment = db.session.get(Payment, payment_id)
    payment.reconciliation_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    monkeypatch.setattr(
        reconciliation_service,
        "query_mpesa_payment_status",
        lambda payment: {
            "state": "manual_review",
            "failure_code": "manual_review_required",
            "failure_message": "M-Pesa reports success, but callback proof is still missing.",
            "raw": {"provider": "mpesa", "result_code": 0},
        },
    )

    response = client.post(
        "/api/v1/admin/payments/reconcile-stale",
        json={"limit": 10},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["manual_review_count"] == 1
    item = response.get_json()["items"][0]
    assert item["id"] == payment_id
    assert item["status"] == "pending"
    assert item["failure_code"] == "manual_review_required"
    assert item["reconciliation_due_at"] is None
