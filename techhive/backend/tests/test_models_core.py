import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Address, Brand, Category, User, UserRole, Vendor, VendorStatus


def create_user(**overrides):
    data = {
        "email": "jane@example.com",
        "password_hash": "hashed-password",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "+254700000001",
        "role": UserRole.CUSTOMER,
    }
    data.update(overrides)
    return User(**data)


def test_user_full_name_property(app):
    user = create_user()

    assert user.full_name == "Jane Doe"


def test_user_can_have_multiple_addresses(app):
    user = create_user()
    address_one = Address(
        label="Home",
        recipient_name=user.full_name,
        phone_number=user.phone_number,
        city="Nairobi",
        address_line_1="Kimathi Street",
        user=user,
    )
    address_two = Address(
        label="Office",
        recipient_name=user.full_name,
        phone_number=user.phone_number,
        city="Nairobi",
        address_line_1="Westlands Road",
        user=user,
    )

    db.session.add_all([user, address_one, address_two])
    db.session.commit()

    saved_user = db.session.get(User, user.id)

    assert len(saved_user.addresses) == 2
    assert {address.label for address in saved_user.addresses} == {"Home", "Office"}


def test_vendor_profile_is_one_to_one_with_user(app):
    user = create_user(role=UserRole.VENDOR, email="vendor@example.com")
    vendor = Vendor(
        user=user,
        business_name="TechHive Gadgets",
        slug="techhive-gadgets",
        phone_number="+254700000002",
        support_email="support@techhivegadgets.com",
        status=VendorStatus.PENDING,
    )

    db.session.add_all([user, vendor])
    db.session.commit()

    saved_user = db.session.get(User, user.id)
    assert saved_user.vendor_profile.business_name == "TechHive Gadgets"


def test_category_slug_must_be_unique(app):
    db.session.add_all(
        [
            Category(name="Smartphones", slug="smartphones"),
            Category(name="Phones", slug="smartphones"),
        ]
    )

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_brand_name_must_be_unique(app):
    db.session.add_all(
        [
            Brand(name="Samsung", slug="samsung"),
            Brand(name="Samsung", slug="samsung-electronics"),
        ]
    )

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
