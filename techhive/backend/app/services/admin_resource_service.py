from __future__ import annotations

from dataclasses import dataclass

from app.extensions import db
from app.models import Banner, Brand, Category, FlashSale, Product, PromoCode, User


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def update_user_active(*, user_id: int, is_active: bool) -> tuple[User | None, ServiceError | None]:
    user = db.session.get(User, user_id)
    if user is None:
        return None, ServiceError({"user": "User not found."}, status_code=404)
    user.is_active = is_active
    return user, None


def update_category(*, category_id: int, payload: dict) -> tuple[Category | None, ServiceError | None]:
    category = db.session.get(Category, category_id)
    if category is None:
        return None, ServiceError({"category": "Category not found."}, status_code=404)

    if "slug" in payload["provided_fields"]:
        duplicate = Category.query.filter(Category.slug == payload["slug"], Category.id != category.id).first()
        if duplicate is not None:
            return None, ServiceError({"slug": "A category with that slug already exists."})

    for field in ("name", "slug", "description", "is_active"):
        if field in payload["provided_fields"]:
            setattr(category, field, payload[field])
    return category, None


def delete_category(*, category_id: int) -> tuple[Category | None, ServiceError | None]:
    category = db.session.get(Category, category_id)
    if category is None:
        return None, ServiceError({"category": "Category not found."}, status_code=404)
    if Product.query.filter_by(category_id=category.id).first() is not None:
        return None, ServiceError({"category": "Categories with products cannot be deleted."})
    db.session.delete(category)
    return category, None


def update_brand(*, brand_id: int, payload: dict) -> tuple[Brand | None, ServiceError | None]:
    brand = db.session.get(Brand, brand_id)
    if brand is None:
        return None, ServiceError({"brand": "Brand not found."}, status_code=404)

    if "slug" in payload["provided_fields"]:
        duplicate = Brand.query.filter(Brand.slug == payload["slug"], Brand.id != brand.id).first()
        if duplicate is not None:
            return None, ServiceError({"slug": "A brand with that slug already exists."})

    for field in ("name", "slug", "description", "website_url", "logo_url", "is_active"):
        if field in payload["provided_fields"]:
            setattr(brand, field, payload[field])
    return brand, None


def delete_brand(*, brand_id: int) -> tuple[Brand | None, ServiceError | None]:
    brand = db.session.get(Brand, brand_id)
    if brand is None:
        return None, ServiceError({"brand": "Brand not found."}, status_code=404)
    if Product.query.filter_by(brand_id=brand.id).first() is not None:
        return None, ServiceError({"brand": "Brands with products cannot be deleted."})
    db.session.delete(brand)
    return brand, None


def update_banner(*, banner_id: int, payload: dict) -> tuple[Banner | None, ServiceError | None]:
    banner = db.session.get(Banner, banner_id)
    if banner is None:
        return None, ServiceError({"banner": "Banner not found."}, status_code=404)
    for field in ("title", "subtitle", "image_url", "link_url", "placement", "sort_order", "is_active"):
        if field in payload["provided_fields"]:
            setattr(banner, field, payload[field])
    return banner, None


def delete_banner(*, banner_id: int) -> tuple[Banner | None, ServiceError | None]:
    banner = db.session.get(Banner, banner_id)
    if banner is None:
        return None, ServiceError({"banner": "Banner not found."}, status_code=404)
    db.session.delete(banner)
    return banner, None


def update_promo_code(*, promo_code_id: int, payload: dict) -> tuple[PromoCode | None, ServiceError | None]:
    promo_code = db.session.get(PromoCode, promo_code_id)
    if promo_code is None:
        return None, ServiceError({"promo_code": "Promo code not found."}, status_code=404)

    if "code" in payload["provided_fields"]:
        duplicate = PromoCode.query.filter(PromoCode.code == payload["code"], PromoCode.id != promo_code.id).first()
        if duplicate is not None:
            return None, ServiceError({"code": "A promo code with that code already exists."})

    for field in ("code", "discount_type", "discount_value", "minimum_order_amount", "is_active"):
        if field in payload["provided_fields"]:
            setattr(promo_code, field, payload[field])
    return promo_code, None


def delete_promo_code(*, promo_code_id: int) -> tuple[PromoCode | None, ServiceError | None]:
    promo_code = db.session.get(PromoCode, promo_code_id)
    if promo_code is None:
        return None, ServiceError({"promo_code": "Promo code not found."}, status_code=404)
    db.session.delete(promo_code)
    return promo_code, None


def update_flash_sale(*, flash_sale_id: int, payload: dict) -> tuple[FlashSale | None, ServiceError | None]:
    flash_sale = db.session.get(FlashSale, flash_sale_id)
    if flash_sale is None:
        return None, ServiceError({"flash_sale": "Flash sale not found."}, status_code=404)
    for field in ("title", "product_id", "sale_price", "starts_at", "ends_at", "is_active"):
        if field in payload["provided_fields"]:
            setattr(flash_sale, field, payload[field])
    return flash_sale, None


def delete_flash_sale(*, flash_sale_id: int) -> tuple[FlashSale | None, ServiceError | None]:
    flash_sale = db.session.get(FlashSale, flash_sale_id)
    if flash_sale is None:
        return None, ServiceError({"flash_sale": "Flash sale not found."}, status_code=404)
    db.session.delete(flash_sale)
    return flash_sale, None
