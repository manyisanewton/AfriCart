from __future__ import annotations

from dataclasses import dataclass

from app.extensions import db
from app.models import OrderItem, Product, Vendor
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
