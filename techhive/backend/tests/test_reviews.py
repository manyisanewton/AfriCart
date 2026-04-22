from app.extensions import db
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.utils.security import hash_password


def create_customer_headers(client, email="review-user@example.com", phone="+254788000111"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "first_name": "Review",
            "last_name": "User",
            "phone_number": phone,
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_review_product():
    vendor_user = User(
        email="vendor-review@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Review",
        phone_number="+254788000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Review Tech",
        slug="review-tech",
        phone_number="+254788000222",
        support_email="support@reviewtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Monitors", slug="monitors")
    brand = Brand(name="LG", slug="lg")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="LG UltraGear 27",
        slug="lg-ultragear-27",
        sku="LG-ULTRAGEAR-27",
        price=56000.00,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_address_for_user(email):
    user = User.query.filter_by(email=email).first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Review User",
        phone_number=user.phone_number,
        country="Kenya",
        city="Nairobi",
        address_line_1="Mama Ngina Street",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def complete_purchase(client, headers, user_email, product_id):
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


def test_verified_buyer_can_create_review(client):
    headers = create_customer_headers(client)
    product = create_review_product()
    complete_purchase(client, headers, "review-user@example.com", product.id)

    response = client.post(
        "/api/v1/reviews",
        json={
            "product_id": product.id,
            "rating": 5,
            "title": "Excellent monitor",
            "comment": "Sharp display and great colors.",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.get_json()["item"]["rating"] == 5


def test_user_cannot_review_without_purchase(client):
    headers = create_customer_headers(client)
    product = create_review_product()

    response = client.post(
        "/api/v1/reviews",
        json={
            "product_id": product.id,
            "rating": 4,
            "comment": "Looks good.",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["product_id"] == (
        "You can only review products you have purchased."
    )


def test_user_cannot_review_same_product_twice(client):
    headers = create_customer_headers(client)
    product = create_review_product()
    complete_purchase(client, headers, "review-user@example.com", product.id)

    first = client.post(
        "/api/v1/reviews",
        json={"product_id": product.id, "rating": 5, "comment": "Excellent."},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/reviews",
        json={"product_id": product.id, "rating": 4, "comment": "Still good."},
        headers=headers,
    )

    assert second.status_code == 400
    assert second.get_json()["error"]["details"]["product_id"] == (
        "You have already reviewed this product."
    )


def test_product_review_listing_returns_summary(client):
    headers = create_customer_headers(client)
    product = create_review_product()
    complete_purchase(client, headers, "review-user@example.com", product.id)
    client.post(
        "/api/v1/reviews",
        json={"product_id": product.id, "rating": 5, "comment": "Excellent."},
        headers=headers,
    )

    response = client.get(f"/api/v1/products/{product.slug}/reviews")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["review_count"] == 1
    assert payload["summary"]["average_rating"] == 5
    assert len(payload["items"]) == 1
