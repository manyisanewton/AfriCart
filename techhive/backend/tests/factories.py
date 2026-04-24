from __future__ import annotations

from app.extensions import db
from app.models import (
    Address,
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    User,
    UserRole,
    Vendor,
    VendorStatus,
)
from app.utils.security import hash_password


def register_user_and_headers(
    client,
    *,
    email: str,
    password: str = "SecurePass123",
    first_name: str,
    last_name: str,
    phone_number: str | None = None,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    user = User.query.filter_by(email=email).first()
    return {"Authorization": f"Bearer {token}"}, user


def create_existing_user(
    *,
    email: str = "existing@example.com",
    first_name: str = "Existing",
    last_name: str = "User",
    phone_number: str | None = "+254700123456",
    role: UserRole = UserRole.CUSTOMER,
):
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123"),
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_admin_headers(
    client,
    *,
    email: str = "admin@example.com",
    first_name: str = "Admin",
    last_name: str = "User",
    phone_number: str = "+254700900001",
):
    headers, user = register_user_and_headers(
        client,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    user.role = UserRole.ADMIN
    db.session.commit()
    return headers


def create_customer_headers(
    client,
    *,
    email: str = "customer@example.com",
    first_name: str = "Customer",
    last_name: str = "User",
    phone_number: str = "+254700900002",
):
    headers, _user = register_user_and_headers(
        client,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    return headers


def create_vendor_user_and_headers(
    client,
    *,
    email: str = "vendor@example.com",
    first_name: str = "Vendor",
    last_name: str = "User",
    phone_number: str = "+254700900003",
    business_name: str = "Vendor Tech",
    slug: str = "vendor-tech",
    support_email: str = "support@vendortech.com",
    status: VendorStatus = VendorStatus.APPROVED,
    is_verified: bool = True,
):
    headers, user = register_user_and_headers(
        client,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    user.role = UserRole.VENDOR
    vendor = Vendor(
        user_id=user.id,
        business_name=business_name,
        slug=slug,
        phone_number=phone_number,
        support_email=support_email,
        status=status,
        is_verified=is_verified,
    )
    db.session.add(vendor)
    db.session.commit()
    return headers, vendor


def create_address_for_user(
    user: User,
    *,
    label: str = "Home",
    recipient_name: str | None = None,
    phone_number: str | None = None,
    country: str = "Kenya",
    city: str = "Nairobi",
    state_or_county: str | None = None,
    postal_code: str | None = None,
    address_line_1: str = "Moi Avenue",
    address_line_2: str | None = None,
    is_default: bool = True,
):
    address = Address(
        user_id=user.id,
        label=label,
        recipient_name=recipient_name or user.full_name,
        phone_number=phone_number or user.phone_number,
        country=country,
        city=city,
        state_or_county=state_or_county,
        postal_code=postal_code,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        is_default=is_default,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_catalog_dependencies(
    *,
    category_name: str = "Wearables",
    category_slug: str = "wearables",
    brand_name: str = "Xiaomi",
    brand_slug: str = "xiaomi",
):
    category = Category(name=category_name, slug=category_slug)
    brand = Brand(name=brand_name, slug=brand_slug)
    db.session.add_all([category, brand])
    db.session.commit()
    return category, brand


def create_product(
    *,
    vendor: Vendor,
    category: Category,
    brand: Brand,
    name: str,
    slug: str,
    sku: str,
    price: float,
    stock_quantity: int,
    short_description: str | None = None,
    description: str | None = None,
    is_active: bool = True,
    is_featured: bool = False,
):
    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name=name,
        slug=slug,
        sku=sku,
        price=price,
        stock_quantity=stock_quantity,
        short_description=short_description,
        description=description,
        is_active=is_active,
        is_featured=is_featured,
    )
    db.session.add(product)
    db.session.commit()
    return product


def seed_catalog():
    vendor_user = create_existing_user(
        email="vendor-catalog@example.com",
        first_name="Vendor",
        last_name="Owner",
        phone_number="+254711000111",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user_id=vendor_user.id,
        business_name="Catalog Tech",
        slug="catalog-tech",
        phone_number="+254711000111",
        support_email="support@catalogtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    smartphones = Category(name="Smartphones", slug="smartphones")
    laptops = Category(name="Laptops", slug="laptops")
    samsung = Brand(name="Samsung", slug="samsung")
    apple = Brand(name="Apple", slug="apple")
    galaxy = Product(
        vendor=vendor,
        category=smartphones,
        brand=samsung,
        name="Samsung Galaxy S24",
        slug="samsung-galaxy-s24",
        sku="GALAXY-S24",
        short_description="Flagship Samsung smartphone",
        description="A fast flagship phone for everyday use.",
        price=99999.00,
        compare_at_price=109999.00,
        stock_quantity=12,
        is_featured=True,
    )
    macbook = Product(
        vendor=vendor,
        category=laptops,
        brand=apple,
        name="MacBook Air M3",
        slug="macbook-air-m3",
        sku="MBA-M3",
        short_description="Thin and light laptop",
        description="A lightweight laptop with long battery life.",
        price=154999.00,
        stock_quantity=7,
        is_featured=False,
    )

    db.session.add_all([vendor, smartphones, laptops, samsung, apple, galaxy, macbook])
    db.session.flush()
    db.session.add_all(
        [
            ProductImage(
                product=galaxy,
                image_url="https://example.com/galaxy-front.jpg",
                alt_text="Samsung Galaxy front view",
                is_primary=True,
                sort_order=0,
            ),
            ProductVariant(
                product=galaxy,
                name="256GB / Black",
                sku="GALAXY-S24-256-BLK",
                price=99999.00,
                stock_quantity=5,
                attribute_summary="256GB, Black",
            ),
        ]
    )
    db.session.commit()


def create_order_for_payment(client, headers, *, user_email: str, product: Product, quantity: int = 1):
    user = User.query.filter_by(email=user_email).first()
    address = create_address_for_user(
        user,
        recipient_name=user.full_name,
        phone_number=user.phone_number,
        state_or_county="Nairobi County",
        postal_code="00100",
    )
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": quantity},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201
    return order_response.get_json()["item"], address
