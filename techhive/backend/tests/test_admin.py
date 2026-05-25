from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from app.services import payment_reconciliation_service as reconciliation_service
from app.extensions import db
from app.models import (
    Address,
    AuditLog,
    Brand,
    Category,
    DeliveryAgent,
    NotificationDelivery,
    NotificationDeliveryStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PlatformSetting,
    Product,
    ProductAttribute,
    Offer,
    OfferBenefit,
    OfferCondition,
    ProductOption,
    ProductRange,
    ProductStockAlert,
    PromoCode,
    RecommendationEvent,
    Review,
    ProductType,
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


def create_customer_headers(client, email="plain-user@example.com", phone="+254777000222"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "first_name": "Plain",
            "last_name": "User",
            "phone_number": phone,
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


def create_address_for_user(email, recipient_name="Review User"):
    user = User.query.filter_by(email=email).first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name=recipient_name,
        phone_number=user.phone_number,
        country="Kenya",
        city="Nairobi",
        address_line_1="Mama Ngina Street",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def complete_purchase_for_user(client, headers, user_email, product_id):
    address = create_address_for_user(user_email)
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
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


def test_admin_can_view_user_detail(client):
    headers = create_admin_headers(client)
    create_customer_headers(client, email="detail-user@example.com", phone="+254777001234")
    user = User.query.filter_by(email="detail-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Detail User",
        phone_number=user.phone_number,
        country="Kenya",
        city="Nairobi",
        address_line_1="Koinange Street",
        is_default=True,
    )
    ticket = SupportTicket(
        user_id=user.id,
        name=user.full_name,
        email=user.email,
        subject="Delivery update",
        message="Where is my order?",
        status=SupportTicketStatus.OPEN,
    )
    db.session.add_all([address, ticket])
    db.session.commit()

    response = client.get(f"/api/v1/admin/users/{user.id}", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()["item"]
    assert payload["email"] == user.email
    assert payload["metrics"]["addresses"] == 1
    assert payload["metrics"]["support_tickets"] == 1
    assert payload["addresses"][0]["label"] == "Home"
    assert payload["recent_support_tickets"][0]["label"] == "Delivery update"


def test_admin_can_create_user(client):
    headers = create_admin_headers(client)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "created-user@example.com",
            "first_name": "Created",
            "last_name": "User",
            "phone_number": "+254777009999",
            "role": "vendor",
            "is_active": True,
            "email_verified": True,
        },
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["email"] == "created-user@example.com"
    assert payload["role"] == "vendor"
    assert payload["email_verified"] is True
    assert payload["must_change_password"] is True
    assert response.get_json()["delivery"]["status"] in {"prepared", "sent", "failed"}
    created = User.query.filter_by(email="created-user@example.com").first()
    assert created is not None
    assert created.must_change_password is True


def test_temporary_password_user_must_change_password_before_access(client):
    admin_headers = create_admin_headers(client)
    create_response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "temp-user@example.com",
            "first_name": "Temp",
            "last_name": "User",
            "role": "customer",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201

    created = User.query.filter_by(email="temp-user@example.com").first()
    created.password_hash = hash_password("TempPass123!")
    db.session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "temp-user@example.com", "password": "TempPass123!"},
    )
    assert login_response.status_code == 200
    access_token = login_response.get_json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["must_change_password"] is True

    blocked_response = client.get("/api/v1/addresses", headers=headers)
    assert blocked_response.status_code == 403

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "TempPass123!", "new_password": "BetterPass123!"},
        headers=headers,
    )
    assert change_response.status_code == 200

    refreshed_me = client.get("/api/v1/auth/me", headers=headers)
    assert refreshed_me.status_code == 200
    assert refreshed_me.get_json()["user"]["must_change_password"] is False


def test_admin_can_create_product(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    category = Category(name="Admin Cameras", slug="admin-cameras")
    brand = Brand(name="Canon", slug="canon")
    db.session.add_all([category, brand])
    db.session.commit()

    response = client.post(
        "/api/v1/admin/products",
        json={
            "vendor_id": vendor.id,
            "category_id": category.id,
            "brand_id": brand.id,
            "name": "Canon EOS R50",
            "slug": "canon-eos-r50",
            "sku": "CANON-R50",
            "price": 125000,
            "stock_quantity": 6,
            "currency": "KES",
            "description": "Mirrorless test camera",
            "is_active": True,
        },
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["name"] == "Canon EOS R50"
    assert payload["vendor"]["id"] == vendor.id
    assert Product.query.filter_by(slug="canon-eos-r50").first() is not None


def test_admin_can_manage_product_types(client):
    headers = create_admin_headers(client)

    create_response = client.post(
        "/api/v1/admin/product-types",
        json={
            "name": "Physical Goods",
            "slug": "physical-goods",
            "requires_shipping": True,
            "track_stock": True,
        },
        headers=headers,
    )

    assert create_response.status_code == 201
    product_type_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/product-types", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    update_response = client.patch(
        f"/api/v1/admin/product-types/{product_type_id}",
        json={
            "requires_shipping": False,
            "track_stock": False,
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["requires_shipping"] is False
    assert update_response.get_json()["item"]["track_stock"] is False

    delete_response = client.delete(f"/api/v1/admin/product-types/{product_type_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(ProductType, product_type_id) is None


def test_admin_can_manage_product_attributes(client):
    headers = create_admin_headers(client)
    product_type_response = client.post(
        "/api/v1/admin/product-types",
        json={
            "name": "Physical Goods",
            "slug": "physical-goods",
            "requires_shipping": True,
            "track_stock": True,
        },
        headers=headers,
    )
    product_type_id = product_type_response.get_json()["item"]["id"]

    create_response = client.post(
        "/api/v1/admin/attributes",
        json={
            "product_type_id": product_type_id,
            "name": "Color",
            "code": "color",
            "type": "text",
            "required": True,
        },
        headers=headers,
    )

    assert create_response.status_code == 201
    attribute_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/attributes", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    update_response = client.patch(
        f"/api/v1/admin/attributes/{attribute_id}",
        json={
            "type": "option",
            "required": False,
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["type"] == "option"
    assert update_response.get_json()["item"]["required"] is False

    delete_response = client.delete(f"/api/v1/admin/attributes/{attribute_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(ProductAttribute, attribute_id) is None


def test_admin_can_manage_product_options(client):
    headers = create_admin_headers(client)

    create_response = client.post(
        "/api/v1/admin/options",
        headers=headers,
        json={
            "name": "Gift message",
            "code": "gift_message",
            "type": "text",
            "required": False,
            "help_text": "Optional note for the package.",
            "order": 1,
        },
    )
    assert create_response.status_code == 201
    option_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/options", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == option_id for item in list_response.get_json()["items"])

    update_response = client.patch(
        f"/api/v1/admin/options/{option_id}",
        headers=headers,
        json={
            "required": True,
            "help_text": "Required for custom packaging.",
            "order": 2,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["item"]
    assert updated["required"] is True
    assert updated["help_text"] == "Required for custom packaging."
    assert updated["order"] == 2

    delete_response = client.delete(f"/api/v1/admin/options/{option_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(ProductOption, option_id) is None


def test_admin_can_manage_offers_foundation(client):
    headers = create_admin_headers(client)

    condition_response = client.post(
        "/api/v1/admin/offers/conditions",
        headers=headers,
        json={
            "type": "value",
            "value": "1500",
            "proxy_class": "ValueCondition",
        },
    )
    assert condition_response.status_code == 201
    condition_id = condition_response.get_json()["item"]["id"]

    benefit_response = client.post(
        "/api/v1/admin/offers/benefits",
        headers=headers,
        json={
            "type": "percentage",
            "value": "10",
            "proxy_class": "PercentageBenefit",
            "max_affected_items": 2,
        },
    )
    assert benefit_response.status_code == 201
    benefit_id = benefit_response.get_json()["item"]["id"]

    meta_response = client.get("/api/v1/admin/offers/meta", headers=headers)
    assert meta_response.status_code == 200
    assert meta_response.get_json()["offer_types"]

    create_offer_response = client.post(
        "/api/v1/admin/offers",
        headers=headers,
        json={
            "name": "Weekend Laptop Offer",
            "slug": "weekend-laptop-offer",
            "description": "10 percent off qualifying laptops.",
            "offer_type": "site",
            "exclusive": True,
            "status": "Open",
            "priority": 10,
            "condition_id": condition_id,
            "benefit_id": benefit_id,
        },
    )
    assert create_offer_response.status_code == 201
    offer_id = create_offer_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/offers", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == offer_id for item in list_response.get_json()["items"])

    update_offer_response = client.patch(
        f"/api/v1/admin/offers/{offer_id}",
        headers=headers,
        json={
            "priority": 12,
            "description": "Updated seasonal laptop offer.",
        },
    )
    assert update_offer_response.status_code == 200
    assert update_offer_response.get_json()["item"]["priority"] == 12

    status_response = client.patch(
        f"/api/v1/admin/offers/{offer_id}/status",
        headers=headers,
        json={"status": "Suspended"},
    )
    assert status_response.status_code == 200
    assert status_response.get_json()["item"]["status"] == "Suspended"

    update_condition_response = client.patch(
        f"/api/v1/admin/offers/conditions/{condition_id}",
        headers=headers,
        json={"value": "2000"},
    )
    assert update_condition_response.status_code == 200
    assert update_condition_response.get_json()["item"]["value"] == "2000"

    update_benefit_response = client.patch(
        f"/api/v1/admin/offers/benefits/{benefit_id}",
        headers=headers,
        json={"max_affected_items": 3},
    )
    assert update_benefit_response.status_code == 200
    assert update_benefit_response.get_json()["item"]["max_affected_items"] == 3

    delete_offer_response = client.delete(f"/api/v1/admin/offers/{offer_id}", headers=headers)
    assert delete_offer_response.status_code == 200
    assert db.session.get(Offer, offer_id) is None

    delete_condition_response = client.delete(f"/api/v1/admin/offers/conditions/{condition_id}", headers=headers)
    assert delete_condition_response.status_code == 200
    assert db.session.get(OfferCondition, condition_id) is None

    delete_benefit_response = client.delete(f"/api/v1/admin/offers/benefits/{benefit_id}", headers=headers)
    assert delete_benefit_response.status_code == 200
    assert db.session.get(OfferBenefit, benefit_id) is None


def test_admin_can_manage_vouchers(client):
    headers = create_admin_headers(client)

    condition_response = client.post(
        "/api/v1/admin/offers/conditions",
        headers=headers,
        json={
            "type": "value",
            "value": "1000",
            "proxy_class": "ValueCondition",
        },
    )
    assert condition_response.status_code == 201
    condition_id = condition_response.get_json()["item"]["id"]

    benefit_response = client.post(
        "/api/v1/admin/offers/benefits",
        headers=headers,
        json={
            "type": "percentage",
            "value": "5",
            "proxy_class": "PercentageBenefit",
        },
    )
    assert benefit_response.status_code == 201
    benefit_id = benefit_response.get_json()["item"]["id"]

    offer_response = client.post(
        "/api/v1/admin/offers",
        headers=headers,
        json={
            "name": "Voucher Offer",
            "slug": "voucher-offer",
            "offer_type": "voucher",
            "status": "Open",
            "condition_id": condition_id,
            "benefit_id": benefit_id,
        },
    )
    assert offer_response.status_code == 201
    offer_id = offer_response.get_json()["item"]["id"]

    create_response = client.post(
        "/api/v1/admin/vouchers",
        headers=headers,
        json={
            "name": "Launch Voucher",
            "code": "LAUNCH100",
            "usage": "Single use",
            "start_datetime": "2026-05-24T10:00:00",
            "end_datetime": "2026-06-24T10:00:00",
        },
    )
    assert create_response.status_code == 201
    voucher_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/vouchers", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == voucher_id for item in list_response.get_json()["items"])

    update_response = client.patch(
        f"/api/v1/admin/vouchers/{voucher_id}",
        headers=headers,
        json={"usage": "Multi-use"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["usage"] == "Multi-use"

    attach_response = client.post(
        f"/api/v1/admin/vouchers/{voucher_id}/offers",
        headers=headers,
        json={"offer_id": offer_id},
    )
    assert attach_response.status_code == 200
    assert len(attach_response.get_json()["item"]["offers"]) == 1

    stats_response = client.get(f"/api/v1/admin/vouchers/{voucher_id}/stats", headers=headers)
    assert stats_response.status_code == 200
    assert stats_response.get_json()["item"]["id"] == voucher_id

    offers_response = client.get(f"/api/v1/admin/vouchers/{voucher_id}/offers", headers=headers)
    assert offers_response.status_code == 200
    assert offers_response.get_json()["items"][0]["id"] == offer_id

    detach_response = client.delete(
        f"/api/v1/admin/vouchers/{voucher_id}/offers",
        headers=headers,
        json={"offer_id": offer_id},
    )
    assert detach_response.status_code == 200
    assert detach_response.get_json()["item"]["offers"] == []

    delete_response = client.delete(f"/api/v1/admin/vouchers/{voucher_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(PromoCode, voucher_id) is None


def test_admin_can_manage_ranges(client):
    headers = create_admin_headers(client)
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    create_response = client.post(
        "/api/v1/admin/ranges",
        headers=headers,
        json={
            "name": "Featured Audio",
            "slug": "featured-audio",
            "description": "Merchandising range for featured audio products.",
            "is_public": True,
            "includes_all_products": False,
        },
    )
    assert create_response.status_code == 201
    range_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/ranges", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == range_id for item in list_response.get_json()["items"])

    update_response = client.patch(
        f"/api/v1/admin/ranges/{range_id}",
        headers=headers,
        json={"includes_all_products": True},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["includes_all_products"] is True

    add_product_response = client.post(
        f"/api/v1/admin/ranges/{range_id}/products",
        headers=headers,
        json={"product_id": product.id},
    )
    assert add_product_response.status_code == 200

    products_response = client.get(f"/api/v1/admin/ranges/{range_id}/products", headers=headers)
    assert products_response.status_code == 200
    assert any(item["id"] == product.id for item in products_response.get_json()["items"])

    remove_product_response = client.delete(
        f"/api/v1/admin/ranges/{range_id}/products",
        headers=headers,
        json={"product_id": product.id},
    )
    assert remove_product_response.status_code == 200

    delete_response = client.delete(f"/api/v1/admin/ranges/{range_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(ProductRange, range_id) is None


def test_admin_can_update_order_operations_fields(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client, email="ops-order@example.com", phone="+254777001234")
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    customer = User.query.filter_by(email="ops-order@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Ops User",
        phone_number="+254777001234",
        country="Kenya",
        city="Nairobi",
        address_line_1="Kimathi Street",
        is_default=True,
    )
    db.session.add(address)

    agent_user = User(
        email="ops-agent@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Ops",
        last_name="Agent",
        phone_number="+254700300400",
        role=UserRole.DELIVERY_AGENT,
    )
    agent = DeliveryAgent(
        user=agent_user,
        display_name="Ops Agent",
        phone_number="+254700300400",
        is_active=True,
    )
    db.session.add_all([agent_user, agent])
    db.session.commit()

    cart_response = client.post(
        "/api/v1/cart/items",
        headers=customer_headers,
        json={"product_id": product.id, "quantity": 1},
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={"address_id": address.id, "notes": "Leave at reception."},
    )
    assert order_response.status_code == 201
    order_id = order_response.get_json()["item"]["id"]

    agents_response = client.get("/api/v1/admin/delivery-agents", headers=headers)
    assert agents_response.status_code == 200
    assert any(item["id"] == agent.id for item in agents_response.get_json()["items"])

    detail_response = client.get(f"/api/v1/admin/orders/{order_id}", headers=headers)
    assert detail_response.status_code == 200

    update_response = client.patch(
        f"/api/v1/admin/orders/{order_id}",
        headers=headers,
        json={
            "status": "confirmed",
            "delivery_status": "assigned",
            "tracking_token": "OPS-TRACK-001",
            "notes": "Packed and ready for dispatch.",
            "delivery_agent_id": agent.id,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["item"]
    assert updated["status"] == "confirmed"
    assert updated["delivery_status"] == "assigned"
    assert updated["tracking_token"] == "OPS-TRACK-001"
    assert updated["notes"] == "Packed and ready for dispatch."
    assert updated["delivery_agent"]["id"] == agent.id


def test_admin_can_view_campaign_summary(client):
    headers = create_admin_headers(client)
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    range_response = client.post(
        "/api/v1/admin/ranges",
        headers=headers,
        json={
            "name": "Campaign Range",
            "slug": "campaign-range",
            "description": "Range for campaign opportunities.",
            "is_public": True,
            "includes_all_products": False,
        },
    )
    assert range_response.status_code == 201

    condition_response = client.post(
        "/api/v1/admin/offers/conditions",
        headers=headers,
        json={"type": "value", "value": "1000"},
    )
    assert condition_response.status_code == 201
    condition_id = condition_response.get_json()["item"]["id"]

    benefit_response = client.post(
        "/api/v1/admin/offers/benefits",
        headers=headers,
        json={"type": "percentage", "value": "10"},
    )
    assert benefit_response.status_code == 201
    benefit_id = benefit_response.get_json()["item"]["id"]

    offer_response = client.post(
        "/api/v1/admin/offers",
        headers=headers,
        json={
            "name": "Campaign Offer",
            "slug": "campaign-offer",
            "offer_type": "site",
            "status": "Open",
            "condition_id": condition_id,
            "benefit_id": benefit_id,
        },
    )
    assert offer_response.status_code == 201

    voucher_response = client.post(
        "/api/v1/admin/vouchers",
        headers=headers,
        json={
            "name": "Campaign Voucher",
            "code": "CAMPAIGN10",
            "usage": "Single use",
            "start_datetime": "2026-05-24T10:00:00",
            "end_datetime": "2026-06-24T10:00:00",
        },
    )
    assert voucher_response.status_code == 201

    summary_response = client.get("/api/v1/admin/campaigns?days=30", headers=headers)
    assert summary_response.status_code == 200
    payload = summary_response.get_json()
    assert payload["range"]["days"] == 30
    assert "kpis" in payload
    assert "campaigns" in payload
    assert "product_opportunities" in payload
    assert any(item["name"] == "Campaign Offer" for item in payload["campaigns"])
    assert any(item["name"] == product.name for item in payload["product_opportunities"])


def test_admin_can_list_and_update_stock_alerts(client):
    headers = create_admin_headers(client)
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    product.stock_quantity = 2
    db.session.commit()

    list_response = client.get("/api/v1/admin/stock-alerts", headers=headers)
    assert list_response.status_code == 200
    items = list_response.get_json()["items"]
    assert items
    alert = next(item for item in items if item["stockrecord"]["product_id"] == product.id)
    assert alert["status"] == "open"
    assert alert["threshold"] == 5

    update_response = client.patch(
        f"/api/v1/admin/stock-alerts/{alert['id']}",
        headers=headers,
        json={"status": "closed"},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["item"]
    assert updated["status"] == "closed"
    assert updated["date_closed"] is not None
    persisted = db.session.get(ProductStockAlert, alert["id"])
    assert persisted is not None
    assert persisted.status == "closed"


def test_admin_can_create_and_update_product_with_low_stock_threshold(client):
    headers = create_admin_headers(client)
    _, vendor = create_vendor_fixture()
    category = Category(name="Threshold Category", slug="threshold-category")
    brand = Brand(name="Threshold Brand", slug="threshold-brand")
    db.session.add_all([category, brand])
    db.session.commit()

    create_response = client.post(
        "/api/v1/admin/products",
        headers=headers,
        json={
            "vendor_id": vendor.id,
            "category_id": category.id,
            "brand_id": brand.id,
            "name": "Threshold Product",
            "slug": "threshold-product",
            "sku": "THRESHOLD-001",
            "price": 1000,
            "currency": "KES",
            "stock_quantity": 7,
            "low_stock_threshold": 3,
            "is_active": True,
            "is_featured": False,
        },
    )
    assert create_response.status_code == 201
    product_id = create_response.get_json()["item"]["id"]
    assert create_response.get_json()["item"]["low_stock_threshold"] == 3

    update_response = client.patch(
        f"/api/v1/admin/products/{product_id}",
        headers=headers,
        json={"low_stock_threshold": 2},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["low_stock_threshold"] == 2

    product = db.session.get(Product, product_id)
    assert product is not None
    assert product.low_stock_threshold == 2


def test_stock_alerts_use_product_specific_threshold(client):
    headers = create_admin_headers(client)
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    product.stock_quantity = 4
    product.low_stock_threshold = 3
    db.session.commit()

    list_response = client.get("/api/v1/admin/stock-alerts", headers=headers)
    assert list_response.status_code == 200
    items = list_response.get_json()["items"]
    assert all(item["stockrecord"]["product_id"] != product.id for item in items)

    product.stock_quantity = 3
    db.session.commit()

    list_response = client.get("/api/v1/admin/stock-alerts", headers=headers)
    assert list_response.status_code == 200
    items = list_response.get_json()["items"]
    alert = next(item for item in items if item["stockrecord"]["product_id"] == product.id)
    assert alert["threshold"] == 3


def test_admin_can_moderate_reviews(client):
    headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client, email="admin-reviewer@example.com", phone="+254788009999")
    _, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)
    complete_purchase_for_user(client, customer_headers, "admin-reviewer@example.com", product.id)
    create_response = client.post(
        "/api/v1/reviews",
        json={
            "product_id": product.id,
            "rating": 4,
            "title": "Good monitor",
            "comment": "Solid panel and decent colors.",
        },
        headers=customer_headers,
    )
    assert create_response.status_code == 201
    review_id = create_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/admin/reviews", headers=headers)
    assert list_response.status_code == 200
    items = list_response.get_json()["items"]
    review = next(item for item in items if item["id"] == review_id)
    assert review["status"] == Review.STATUS_MODERATION

    update_response = client.patch(
        f"/api/v1/admin/reviews/{review_id}",
        headers=headers,
        json={
            "status": Review.STATUS_APPROVED,
            "title": "Excellent monitor",
            "body": "Excellent contrast and colors.",
            "score": 5,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["item"]
    assert updated["status"] == Review.STATUS_APPROVED
    assert updated["title"] == "Excellent monitor"
    assert updated["body"] == "Excellent contrast and colors."
    assert updated["score"] == 5

    delete_response = client.delete(f"/api/v1/admin/reviews/{review_id}", headers=headers)
    assert delete_response.status_code == 200
    assert db.session.get(Review, review_id) is None


def test_admin_can_manage_media_library(client):
    headers = create_admin_headers(client)
    vendor_user, vendor = create_vendor_fixture()
    product = create_product_fixture(vendor)

    upload_response = client.post(
        "/api/v1/admin/media",
        data={
            "product_id": str(product.id),
            "alt": "Front product shot",
            "image": (BytesIO(b"fake-image-bytes"), "product-shot.png"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 201
    upload_payload = upload_response.get_json()["item"]
    assert upload_payload["product_id"] == product.id
    assert upload_payload["url"].startswith("/media/products/")

    list_response = client.get("/api/v1/admin/media", headers=headers)

    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert list_payload["summary"]["total"] == 1
    assert list_payload["summary"]["matching"] == 1
    assert list_payload["items"][0]["id"] == upload_payload["id"]

    delete_response = client.delete(f"/api/v1/admin/media/{upload_payload['id']}", headers=headers)

    assert delete_response.status_code == 200
    refreshed_product = db.session.get(Product, product.id)
    assert refreshed_product is not None
    assert len(refreshed_product.images) == 0


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


def test_admin_can_create_child_category(client):
    headers = create_admin_headers(client)
    parent_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Electronics", "slug": "electronics"},
        headers=headers,
    )
    parent_id = parent_response.get_json()["item"]["id"]

    child_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Speakers", "slug": "speakers", "parent_id": parent_id},
        headers=headers,
    )

    assert child_response.status_code == 201
    payload = child_response.get_json()["item"]
    assert payload["parent_id"] == parent_id
    assert payload["depth"] == 2


def test_admin_can_move_category_under_parent(client):
    headers = create_admin_headers(client)
    root_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Electronics", "slug": "electronics"},
        headers=headers,
    )
    child_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Audio", "slug": "audio"},
        headers=headers,
    )
    root_id = root_response.get_json()["item"]["id"]
    child_id = child_response.get_json()["item"]["id"]

    update_response = client.patch(
        f"/api/v1/admin/categories/{child_id}",
        json={"parent_id": root_id},
        headers=headers,
    )

    assert update_response.status_code == 200
    payload = update_response.get_json()["item"]
    assert payload["parent_id"] == root_id
    assert payload["depth"] == 2


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


def test_admin_cannot_delete_category_with_children(client):
    headers = create_admin_headers(client)
    parent_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "Electronics", "slug": "electronics"},
        headers=headers,
    )
    parent_id = parent_response.get_json()["item"]["id"]
    client.post(
        "/api/v1/admin/categories",
        json={"name": "Speakers", "slug": "speakers", "parent_id": parent_id},
        headers=headers,
    )

    response = client.delete(f"/api/v1/admin/categories/{parent_id}", headers=headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["category"] == (
        "Categories with child categories cannot be deleted."
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
