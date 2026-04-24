from __future__ import annotations

from dataclasses import dataclass

from app.models import Brand, Category, Product, PromoCode


@dataclass
class ValidationLookupError:
    details: dict[str, str]


def get_active_category(category_id: int) -> tuple[Category | None, ValidationLookupError | None]:
    category = Category.query.filter_by(id=category_id, is_active=True).first()
    if category is None:
        return None, ValidationLookupError({"category_id": "Selected category was not found."})
    return category, None


def get_active_brand(brand_id: int) -> tuple[Brand | None, ValidationLookupError | None]:
    brand = Brand.query.filter_by(id=brand_id, is_active=True).first()
    if brand is None:
        return None, ValidationLookupError({"brand_id": "Selected brand was not found."})
    return brand, None


def get_product_for_flash_sale(product_id: int) -> tuple[Product | None, ValidationLookupError | None]:
    product = Product.query.filter_by(id=product_id).first()
    if product is None:
        return None, ValidationLookupError({"product_id": "Selected product was not found."})
    return product, None


def ensure_unique_category_slug(slug: str) -> ValidationLookupError | None:
    if Category.query.filter_by(slug=slug).first():
        return ValidationLookupError({"slug": "A category with that slug already exists."})
    return None


def ensure_unique_brand_slug(slug: str) -> ValidationLookupError | None:
    if Brand.query.filter_by(slug=slug).first():
        return ValidationLookupError({"slug": "A brand with that slug already exists."})
    return None


def ensure_unique_product_slug_and_sku(*, slug: str, sku: str) -> ValidationLookupError | None:
    if Product.query.filter_by(slug=slug).first():
        return ValidationLookupError({"slug": "A product with that slug already exists."})
    if Product.query.filter_by(sku=sku).first():
        return ValidationLookupError({"sku": "A product with that SKU already exists."})
    return None


def ensure_unique_product_slug_and_sku_for_update(
    *,
    slug: str | None,
    sku: str | None,
    product_id: int,
) -> ValidationLookupError | None:
    if slug is not None:
        duplicate_slug = Product.query.filter(
            Product.slug == slug,
            Product.id != product_id,
        ).first()
        if duplicate_slug is not None:
            return ValidationLookupError({"slug": "A product with that slug already exists."})
    if sku is not None:
        duplicate_sku = Product.query.filter(
            Product.sku == sku,
            Product.id != product_id,
        ).first()
        if duplicate_sku is not None:
            return ValidationLookupError({"sku": "A product with that SKU already exists."})
    return None


def ensure_unique_promo_code(code: str) -> ValidationLookupError | None:
    if PromoCode.query.filter_by(code=code).first():
        return ValidationLookupError({"code": "A promo code with that code already exists."})
    return None
