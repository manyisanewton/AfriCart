from app.extensions import db
from app.models import (
    Address,
    Brand,
    Category,
    DeliveryAgent,
    DeliveryZone,
    Product,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.utils.security import hash_password


def create_admin_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "delivery-admin@example.com",
            "password": "SecurePass123",
            "first_name": "Delivery",
            "last_name": "Admin",
            "phone_number": "+254700101001",
        },
    )
    user = User.query.filter_by(email="delivery-admin@example.com").first()
    user.role = UserRole.ADMIN
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "delivery-customer@example.com",
            "password": "SecurePass123",
            "first_name": "Delivery",
            "last_name": "Customer",
            "phone_number": "+254700101002",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_delivery_agent_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "delivery-agent@example.com",
            "password": "SecurePass123",
            "first_name": "Delivery",
            "last_name": "Agent",
            "phone_number": "+254700101003",
        },
    )
    user = User.query.filter_by(email="delivery-agent@example.com").first()
    user.role = UserRole.DELIVERY_AGENT
    agent = DeliveryAgent(
        user_id=user.id,
        display_name="Agent One",
        phone_number="+254700101003",
        is_active=True,
    )
    db.session.add(agent)
    db.session.commit()
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, agent


def seed_zone():
    zone = DeliveryZone(
        name="Nairobi Urban",
        city="Nairobi",
        fee=450.00,
        estimated_days_min=1,
        estimated_days_max=2,
        is_active=True,
    )
    db.session.add(zone)
    db.session.commit()
    return zone


def seed_product():
    vendor_user = User(
        email="delivery-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Delivery",
        last_name="Vendor",
        phone_number="+254700101004",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Delivery Tech",
        slug="delivery-tech",
        phone_number="+254700101004",
        support_email="support@deliverytech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Printers", slug="printers")
    brand = Brand(name="Canon", slug="canon")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Canon PIXMA G3430",
        slug="canon-pixma-g3430",
        sku="CANON-G3430",
        price=32000.00,
        stock_quantity=4,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def seed_address():
    user = User.query.filter_by(email="delivery-customer@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Delivery Customer",
        phone_number="+254700101002",
        country="Kenya",
        city="Nairobi",
        address_line_1="Kimathi Street",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_order(client, customer_headers):
    seed_zone()
    product = seed_product()
    address = seed_address()
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


def test_delivery_estimate_returns_zone(client):
    seed_zone()

    response = client.get("/api/v1/delivery/estimate?city=Nairobi")

    assert response.status_code == 200
    assert response.get_json()["item"]["fee"] == "450.00"


def test_order_tracking_returns_created_order(client):
    customer_headers = create_customer_headers(client)
    order = create_order(client, customer_headers)

    response = client.get(f"/api/v1/delivery/track/{order['tracking_token']}")

    assert response.status_code == 200
    assert response.get_json()["item"]["order_number"] == order["order_number"]


def test_admin_can_assign_delivery_agent(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    _, agent = create_delivery_agent_headers(client)
    order = create_order(client, customer_headers)

    response = client.post(
        f"/api/v1/delivery/orders/{order['id']}/assign-agent",
        json={"delivery_agent_id": agent.id},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["delivery_agent"]["id"] == agent.id


def test_delivery_agent_can_update_status(client):
    admin_headers = create_admin_headers(client)
    customer_headers = create_customer_headers(client)
    agent_headers, agent = create_delivery_agent_headers(client)
    order = create_order(client, customer_headers)
    assign_response = client.post(
        f"/api/v1/delivery/orders/{order['id']}/assign-agent",
        json={"delivery_agent_id": agent.id},
        headers=admin_headers,
    )
    assert assign_response.status_code == 200

    response = client.post(
        f"/api/v1/delivery/orders/{order['id']}/status",
        json={"delivery_status": "in_transit"},
        headers=agent_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["delivery_status"] == "in_transit"
