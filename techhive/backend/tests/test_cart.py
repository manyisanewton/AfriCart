from app.extensions import db
from app.models import (
    Brand,
    Category,
    Product,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.utils.security import hash_password


def auth_headers(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cart-user@example.com",
            "password": "SecurePass123",
            "first_name": "Cart",
            "last_name": "User",
            "phone_number": "+254733000111",
        },
    )
    token = register_response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product_for_authenticated_user():
    vendor_user = User(
        email="vendor-auth-cart@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Auth",
        phone_number="+254733000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Auth Cart Tech",
        slug="auth-cart-tech",
        phone_number="+254733000222",
        support_email="support@authcarttech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Chargers", slug="chargers")
    brand = Brand(name="Baseus", slug="baseus")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Baseus GaN Charger",
        slug="baseus-gan-charger",
        sku="BASEUS-GAN-65W",
        price=3200.00,
        stock_quantity=6,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def test_add_item_to_cart(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()

    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["quantity"] == 2
    assert payload["product"]["slug"] == "baseus-gan-charger"


def test_get_cart_returns_summary(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()
    client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 2},
        headers=headers,
    )

    response = client.get("/api/v1/cart", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["items_count"] == 2
    assert payload["summary"]["subtotal"] == "6400.00"


def test_add_item_to_cart_rejects_excess_stock(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()

    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 99},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["quantity"] == (
        "Requested quantity exceeds available stock."
    )


def test_update_cart_item_quantity(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()
    add_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    item_id = add_response.get_json()["item"]["id"]

    response = client.patch(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 3},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["quantity"] == 3


def test_delete_cart_item(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()
    add_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    item_id = add_response.get_json()["item"]["id"]

    response = client.delete(f"/api/v1/cart/items/{item_id}", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["message"] == "Cart item removed."


def test_add_and_remove_wishlist_item(client):
    headers = auth_headers(client)
    product = create_product_for_authenticated_user()

    add_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": product.id},
        headers=headers,
    )

    assert add_response.status_code == 201
    item_id = add_response.get_json()["item"]["id"]

    list_response = client.get("/api/v1/wishlist", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    delete_response = client.delete(f"/api/v1/wishlist/items/{item_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Wishlist item removed."
