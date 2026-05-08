from __future__ import annotations

from dataclasses import dataclass

from app.extensions import db
from app.models import OrderItem, Product, ProductImage, ProductVariant, Vendor
from app.services.catalog_validation_service import (
    ensure_unique_product_slug_and_sku_for_update,
    get_active_brand,
    get_active_category,
)


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def get_vendor_product(*, vendor_id: int, product_id: int) -> Product | None:
    return Product.query.filter_by(id=product_id, vendor_id=vendor_id).first()


def update_vendor_product(
    *,
    vendor: Vendor,
    product_id: int,
    payload: dict,
) -> tuple[Product | None, ServiceError | None]:
    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    uniqueness_error = ensure_unique_product_slug_and_sku_for_update(
        slug=payload.get("slug") if "slug" in payload["provided_fields"] else None,
        sku=payload.get("sku") if "sku" in payload["provided_fields"] else None,
        product_id=product.id,
    )
    if uniqueness_error is not None:
        return None, ServiceError(uniqueness_error.details)

    if "category_id" in payload["provided_fields"]:
        category, category_error = get_active_category(payload["category_id"])
        if category_error:
            return None, ServiceError(category_error.details)
        product.category_id = category.id

    if "brand_id" in payload["provided_fields"]:
        brand, brand_error = get_active_brand(payload["brand_id"])
        if brand_error:
            return None, ServiceError(brand_error.details)
        product.brand_id = brand.id

    simple_fields = [
        "name",
        "slug",
        "sku",
        "price",
        "stock_quantity",
        "short_description",
        "description",
        "is_active",
        "is_featured",
    ]
    for field in simple_fields:
        if field in payload["provided_fields"]:
            setattr(product, field, payload[field])

    return product, None


def delete_vendor_product(*, vendor: Vendor, product_id: int) -> tuple[Product | None, ServiceError | None]:
    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    existing_order_item = OrderItem.query.filter_by(product_id=product.id).first()
    if existing_order_item is not None:
        return None, ServiceError(
            {"product": "Products that are part of existing orders cannot be deleted."}
        )

    db.session.delete(product)
    return product, None


def get_vendor_variant(*, vendor_id: int, product_id: int, variant_id: int) -> ProductVariant | None:
    return (
        ProductVariant.query.join(Product)
        .filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
            Product.vendor_id == vendor_id,
        )
        .first()
    )


def ensure_unique_variant_sku(*, sku: str, variant_id: int | None = None) -> ServiceError | None:
    existing_variant = ProductVariant.query.filter_by(sku=sku).first()
    if existing_variant is not None and existing_variant.id != variant_id:
        return ServiceError({"sku": "A variant with that SKU already exists."})

    existing_product = Product.query.filter_by(sku=sku).first()
    if existing_product is not None:
        return ServiceError({"sku": "A product already uses that SKU."})
    return None


def create_vendor_variant(
    *,
    vendor: Vendor,
    product_id: int,
    payload: dict,
) -> tuple[ProductVariant | None, ServiceError | None]:
    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    uniqueness_error = ensure_unique_variant_sku(sku=payload["sku"])
    if uniqueness_error is not None:
        return None, uniqueness_error

    variant = ProductVariant(product_id=product.id, **payload)
    db.session.add(variant)
    return variant, None


def update_vendor_variant(
    *,
    vendor: Vendor,
    product_id: int,
    variant_id: int,
    payload: dict,
) -> tuple[ProductVariant | None, ServiceError | None]:
    variant = get_vendor_variant(vendor_id=vendor.id, product_id=product_id, variant_id=variant_id)
    if variant is None:
        return None, ServiceError({"variant": "Variant not found."}, status_code=404)

    if "sku" in payload["provided_fields"]:
        uniqueness_error = ensure_unique_variant_sku(sku=payload["sku"], variant_id=variant.id)
        if uniqueness_error is not None:
            return None, uniqueness_error

    for field in ("name", "sku", "price", "stock_quantity", "attribute_summary"):
        if field in payload["provided_fields"]:
            setattr(variant, field, payload[field])

    return variant, None


def delete_vendor_variant(
    *,
    vendor: Vendor,
    product_id: int,
    variant_id: int,
) -> tuple[ProductVariant | None, ServiceError | None]:
    variant = get_vendor_variant(vendor_id=vendor.id, product_id=product_id, variant_id=variant_id)
    if variant is None:
        return None, ServiceError({"variant": "Variant not found."}, status_code=404)

    db.session.delete(variant)
    return variant, None


def update_vendor_product_image(
    *,
    vendor: Vendor,
    product_id: int,
    image_id: int,
    payload: dict,
) -> tuple[ProductImage | None, ServiceError | None]:
    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    image = ProductImage.query.filter_by(id=image_id, product_id=product.id).first()
    if image is None:
        return None, ServiceError({"image": "Image not found."}, status_code=404)

    if "alt_text" in payload["provided_fields"]:
        image.alt_text = payload["alt_text"]
    if "sort_order" in payload["provided_fields"]:
        image.sort_order = payload["sort_order"]
    if "is_primary" in payload["provided_fields"] and payload["is_primary"]:
        for existing_image in product.images:
            existing_image.is_primary = existing_image.id == image.id
    elif "is_primary" in payload["provided_fields"] and not payload["is_primary"]:
        image.is_primary = False
        if not any(candidate.is_primary for candidate in product.images if candidate.id != image.id):
            replacement = next((candidate for candidate in product.images if candidate.id != image.id), None)
            if replacement is not None:
                replacement.is_primary = True

    return image, None


def list_low_stock_products(*, vendor: Vendor, threshold: int) -> list[Product]:
    return (
        Product.query.filter(
            Product.vendor_id == vendor.id,
            Product.stock_quantity <= threshold,
        )
        .order_by(Product.stock_quantity.asc(), Product.id.asc())
        .all()
    )
