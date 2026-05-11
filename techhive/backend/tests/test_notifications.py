from app.extensions import db
from app.models import (
    Address,
    Brand,
    Category,
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationPreference,
    NotificationType,
    Product,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.services.email_service import render_email_template
from app.utils.security import hash_password
from tests.factories import create_admin_headers as create_admin_headers_base


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "notify-user@example.com",
            "password": "SecurePass123",
            "first_name": "Notify",
            "last_name": "User",
            "phone_number": "+254799000111",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_admin_headers(client):
    return create_admin_headers_base(
        client,
        email="notify-admin@example.com",
        first_name="Notify",
        last_name="Admin",
        phone_number="+254799900999",
    )


def create_notification_product():
    vendor_user = User(
        email="vendor-notify@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Notify",
        phone_number="+254799000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Notify Tech",
        slug="notify-tech",
        phone_number="+254799000222",
        support_email="support@notifytech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Projectors", slug="projectors")
    brand = Brand(name="Epson", slug="epson")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Epson EB-FH06",
        slug="epson-eb-fh06",
        sku="EPSON-EB-FH06",
        price=78000.00,
        stock_quantity=3,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_address_for_notification_user():
    user = User.query.filter_by(email="notify-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Notify User",
        phone_number="+254799000111",
        country="Kenya",
        city="Nairobi",
        address_line_1="Haile Selassie Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_order_and_payment(client, headers):
    product = create_notification_product()
    address = create_address_for_notification_user()

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201
    order = order_response.get_json()["item"]

    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    assert payment_response.status_code in (200, 201)
    payment = payment_response.get_json()["item"]
    return order, payment


def test_notifications_list_includes_order_and_payment_events(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.get("/api/v1/notifications", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total"] >= 2
    assert payload["summary"]["unread_count"] >= 2


def test_mark_single_notification_read(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)
    list_response = client.get("/api/v1/notifications", headers=headers)
    notification_id = list_response.get_json()["items"][0]["id"]

    response = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["is_read"] is True


def test_mark_all_notifications_read(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.post("/api/v1/notifications/read-all", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["updated_count"] >= 2

    list_response = client.get("/api/v1/notifications", headers=headers)
    assert list_response.status_code == 200
    assert list_response.get_json()["summary"]["unread_count"] == 0


def test_payment_paid_creates_notification(client):
    headers = create_customer_headers(client)
    _, payment = create_order_and_payment(client, headers)

    paid_response = client.post(
        f"/api/v1/payments/{payment['id']}/mark-paid",
        headers=headers,
    )
    assert paid_response.status_code == 200

    list_response = client.get("/api/v1/notifications", headers=headers)
    types = [item["type"] for item in list_response.get_json()["items"]]
    assert "payment_paid" in types


def test_refund_request_and_admin_update_use_refund_template(client, monkeypatch):
    headers = create_customer_headers(client)
    admin_headers = create_admin_headers(client)
    order, payment = create_order_and_payment(client, headers)

    paid_response = client.post(
        f"/api/v1/payments/{payment['id']}/mark-paid",
        headers=headers,
    )
    assert paid_response.status_code == 200

    sent = []

    def fake_send_email(**kwargs):
        sent.append(kwargs)
        return {
            "channel": "email",
            "status": "sent",
            "recipient": kwargs["to_email"],
            "template": kwargs["template"],
            "subject": kwargs["subject"],
        }

    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        fake_send_email,
    )
    monkeypatch.setattr(
        "app.services.major_notification_service.send_email",
        fake_send_email,
    )

    refund_response = client.post(
        f"/api/v1/orders/{order['id']}/refund-request",
        json={"reason": "Changed my mind"},
        headers=headers,
    )
    assert refund_response.status_code == 201
    assert sent[-1]["template"] == "refund_status"

    admin_update_response = client.patch(
        f"/api/v1/admin/refunds/{refund_response.get_json()['item']['id']}/status",
        json={"status": "processed", "admin_note": "Approved and completed."},
        headers=admin_headers,
    )
    assert admin_update_response.status_code == 200
    assert sent[-1]["template"] == "refund_status"

    deliveries = NotificationDelivery.query.filter_by(channel=NotificationChannel.EMAIL).all()
    assert any(delivery.template == "refund_status" for delivery in deliveries)


def test_support_ticket_create_and_status_update_use_support_template(client, monkeypatch):
    admin_headers = create_admin_headers(client)
    sent = []

    def fake_send_email(**kwargs):
        sent.append(kwargs)
        return {
            "channel": "email",
            "status": "sent",
            "recipient": kwargs["to_email"],
            "template": kwargs["template"],
            "subject": kwargs["subject"],
        }

    monkeypatch.setattr(
        "app.services.major_notification_service.send_email",
        fake_send_email,
    )
    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        fake_send_email,
    )

    create_response = client.post(
        "/api/v1/support/tickets",
        json={
            "name": "Notify User",
            "email": "notify-user@example.com",
            "phone_number": "+254799000111",
            "subject": "Need delivery help",
            "message": "Please help with tracking.",
            "category": "delivery",
        },
    )
    assert create_response.status_code == 201
    assert sent[-1]["template"] == "support_ticket"

    ticket_id = create_response.get_json()["item"]["id"]
    update_response = client.patch(
        f"/api/v1/admin/support-tickets/{ticket_id}/status",
        json={"status": "resolved", "admin_note": "Tracking details shared."},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert sent[-1]["template"] == "support_ticket"


def test_notification_preferences_default_and_update(client):
    headers = create_customer_headers(client)

    get_response = client.get("/api/v1/notifications/preferences", headers=headers)
    assert get_response.status_code == 200
    assert get_response.get_json()["item"]["email_enabled"] is True
    assert get_response.get_json()["item"]["sms_enabled"] is False

    patch_response = client.patch(
        "/api/v1/notifications/preferences",
        json={
            "sms_enabled": True,
            "transactional_sms_enabled": True,
            "marketing_email_enabled": True,
        },
        headers=headers,
    )

    assert patch_response.status_code == 200
    item = patch_response.get_json()["item"]
    assert item["sms_enabled"] is True
    assert item["transactional_sms_enabled"] is True
    assert item["marketing_email_enabled"] is True


def test_user_can_list_notification_deliveries(client):
    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.get("/api/v1/notifications/deliveries", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total"] >= 2
    assert any(item["channel"] == "email" for item in payload["items"])
    assert any(item["channel"] == "in_app" for item in payload["items"])


def test_order_created_dispatches_email_when_enabled(client, monkeypatch):
    headers = create_customer_headers(client)
    product = create_notification_product()
    address = create_address_for_notification_user()
    sent = []

    def fake_send_email(**kwargs):
        sent.append(kwargs)
        return {"channel": "email", "status": "sent", "recipient": kwargs["to_email"]}

    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        fake_send_email,
    )

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )

    assert order_response.status_code == 201
    assert len(sent) == 1
    assert sent[0]["template"] == "order_confirmation"


def test_order_created_skips_email_when_transactional_email_disabled(client, monkeypatch):
    headers = create_customer_headers(client)
    product = create_notification_product()
    address = create_address_for_notification_user()
    client.patch(
        "/api/v1/notifications/preferences",
        json={"transactional_email_enabled": False},
        headers=headers,
    )
    sent = []

    def fake_send_email(**kwargs):
        sent.append(kwargs)
        return {"channel": "email", "status": "sent", "recipient": kwargs["to_email"]}

    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        fake_send_email,
    )

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )

    assert order_response.status_code == 201
    assert sent == []


def test_admin_bulk_notifications_create_announcements_and_record_paused_sms(client, monkeypatch):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-notify@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Notify",
            "phone_number": "+254799100100",
        },
    )
    admin_user = User.query.filter_by(email="admin-notify@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    create_customer_headers(client)
    second_headers = client.post(
        "/api/v1/auth/register",
        json={
            "email": "notify-second@example.com",
            "password": "SecurePass123",
            "first_name": "Second",
            "last_name": "User",
            "phone_number": "+254799000333",
        },
    )
    assert second_headers.status_code == 201

    for email in ("notify-user@example.com", "notify-second@example.com"):
        user = User.query.filter_by(email=email).first()
        user.notification_preference = NotificationPreference(
            user_id=user.id,
            sms_enabled=True,
            transactional_sms_enabled=True,
            email_enabled=True,
            transactional_email_enabled=True,
        )
    db.session.commit()

    sent_emails = []
    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        lambda **kwargs: sent_emails.append(kwargs) or {
            "channel": "email",
            "status": "sent",
            "recipient": kwargs["to_email"],
        },
    )

    response = client.post(
        "/api/v1/admin/notifications/bulk",
        json={
            "title": "Maintenance window",
            "message": "We will be performing scheduled maintenance tonight.",
            "channels": ["in_app", "email", "sms"],
            "role": "customer",
            "sms_message": "TechHive: scheduled maintenance tonight.",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["targeted_count"] >= 2
    assert len(sent_emails) >= 2
    assert payload["bulk_sms"]["status"] == "skipped"
    assert payload["bulk_sms"]["reason"] == "sms_paused"
    assert payload["bulk_sms"]["recipient_count"] >= 1
    announcement_count = Notification.query.filter_by(type=NotificationType.ADMIN_ANNOUNCEMENT).count()
    assert announcement_count >= 2

    deliveries = NotificationDelivery.query.filter_by(channel=NotificationChannel.EMAIL).all()
    assert len(deliveries) >= 2
    skipped_sms = NotificationDelivery.query.filter_by(channel=NotificationChannel.SMS).all()
    assert skipped_sms
    assert all(delivery.status == NotificationDeliveryStatus.SKIPPED for delivery in skipped_sms)
    assert all(delivery.reason == "sms_paused" for delivery in skipped_sms)


def test_render_email_template_returns_styled_html(app):
    with app.app_context():
        rendered = render_email_template(
            "admin_announcement",
            {"headline": "Platform update", "message": "A styled message."},
        )

    assert "linear-gradient" in rendered["html"]
    assert "Platform update" in rendered["html"]
    assert "A styled message." in rendered["text"]


def test_render_refund_and_support_templates_returns_styled_html(app):
    with app.app_context():
        refund_rendered = render_email_template(
            "refund_status",
            {
                "headline": "Refund update",
                "order_number": "TH-001",
                "refund_amount": "5000.00",
                "status_label": "Processed",
            },
        )
        support_rendered = render_email_template(
            "support_ticket",
            {
                "headline": "Support update",
                "ticket_subject": "Need help",
                "ticket_category": "delivery",
                "ticket_status": "Resolved",
            },
        )

    assert "Refund update" in refund_rendered["html"]
    assert "KES 5000.00" in refund_rendered["html"]
    assert "Support update" in support_rendered["html"]
    assert "Need help" in support_rendered["html"]


def test_admin_can_retry_failed_email_delivery(client, monkeypatch):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-retry@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Retry",
            "phone_number": "+254799100101",
        },
    )
    admin_user = User.query.filter_by(email="admin-retry@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)
    failed_delivery = NotificationDelivery.query.filter(
        NotificationDelivery.channel == "email"
    ).first()
    failed_delivery.status = NotificationDeliveryStatus.FAILED
    failed_delivery.reason = "smtp timeout"
    db.session.commit()

    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        lambda **kwargs: {
            "channel": "email",
            "status": "sent",
            "recipient": kwargs["to_email"],
            "subject": kwargs["subject"],
            "template": kwargs["template"],
        },
    )

    response = client.post(
        "/api/v1/admin/notification-deliveries/retry",
        json={"delivery_id": failed_delivery.id},
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["item"]["status"] == "sent"
    assert payload["item"]["retry_count"] == 1


def test_admin_can_list_notification_deliveries_with_filters(client):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-log@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Logs",
            "phone_number": "+254799100111",
        },
    )
    admin_user = User.query.filter_by(email="admin-log@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    headers = create_customer_headers(client)
    create_order_and_payment(client, headers)

    response = client.get(
        "/api/v1/admin/notification-deliveries?channel=email&status=prepared",
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total"] >= 1
    assert all(item["channel"] == "email" for item in payload["items"])
    assert all(item["status"] == "prepared" for item in payload["items"])


def test_admin_notification_delivery_filters_reject_invalid_values(client):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-invalid-filters@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Invalid",
            "phone_number": "+254799100121",
        },
    )
    admin_user = User.query.filter_by(email="admin-invalid-filters@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    response = client.get(
        "/api/v1/admin/notification-deliveries?channel=push&status=done",
        headers=admin_headers,
    )

    assert response.status_code == 400
    errors = response.get_json()["error"]["details"]
    assert "status" in errors or "channel" in errors


def test_admin_can_send_bulk_email_campaign(client, monkeypatch):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-bulk-email@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "Mailer",
            "phone_number": "+254799100131",
        },
    )
    admin_user = User.query.filter_by(email="admin-bulk-email@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    create_customer_headers(client)
    second_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bulk-email-second@example.com",
            "password": "SecurePass123",
            "first_name": "Second",
            "last_name": "Recipient",
            "phone_number": "+254799000444",
        },
    )
    assert second_response.status_code == 201

    for email in ("notify-user@example.com", "bulk-email-second@example.com"):
        user = User.query.filter_by(email=email).first()
        user.notification_preference = NotificationPreference(
            user_id=user.id,
            email_enabled=True,
            marketing_email_enabled=True,
        )
    db.session.commit()

    sent_emails = []
    monkeypatch.setattr(
        "app.services.notification_dispatch_service.send_email",
        lambda **kwargs: sent_emails.append(kwargs) or {
            "channel": "email",
            "status": "sent",
            "recipient": kwargs["to_email"],
            "subject": kwargs["subject"],
            "template": kwargs["template"],
        },
    )

    response = client.post(
        "/api/v1/admin/emails/bulk",
        json={
            "subject": "Storefront refresh",
            "headline": "A better TechHive is landing",
            "message": "We have upgraded discovery, delivery visibility, and support operations.",
            "preheader": "Platform improvements are now available.",
            "cta_label": "See what changed",
            "cta_url": "https://example.com/updates",
            "role": "customer",
            "is_marketing": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "live"
    assert payload["targeted_count"] >= 2
    assert payload["summary"]["sent"] >= 2
    assert len(sent_emails) >= 2
    assert sent_emails[0]["template"] == "admin_announcement"
    assert sent_emails[0]["context"]["cta_label"] == "See what changed"


def test_admin_can_dry_run_bulk_email_campaign(client):
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-dry-run@example.com",
            "password": "SecurePass123",
            "first_name": "Admin",
            "last_name": "DryRun",
            "phone_number": "+254799100141",
        },
    )
    admin_user = User.query.filter_by(email="admin-dry-run@example.com").first()
    admin_user.role = UserRole.ADMIN
    db.session.commit()
    admin_headers = {
        "Authorization": f"Bearer {admin_response.get_json()['tokens']['access_token']}"
    }

    create_customer_headers(client)

    response = client.post(
        "/api/v1/admin/emails/bulk",
        json={
            "subject": "Dry run email",
            "message": "Preview only, no outbound email should be attempted.",
            "role": "customer",
            "dry_run": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "dry_run"
    assert payload["targeted_count"] >= 1
    assert payload["results"] == []
    assert payload["summary"]["sent"] == 0
