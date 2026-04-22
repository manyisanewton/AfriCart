from decimal import Decimal
from datetime import timezone


def _money(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def _iso_datetime(value) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_category(category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_active": category.is_active,
    }


def serialize_brand(brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description,
        "website_url": brand.website_url,
        "logo_url": brand.logo_url,
        "is_active": brand.is_active,
    }


def serialize_product_image(image) -> dict:
    return {
        "id": image.id,
        "image_url": image.image_url,
        "alt_text": image.alt_text,
        "is_primary": image.is_primary,
        "sort_order": image.sort_order,
    }


def serialize_product_variant(variant) -> dict:
    return {
        "id": variant.id,
        "name": variant.name,
        "sku": variant.sku,
        "price": _money(variant.price),
        "stock_quantity": variant.stock_quantity,
        "attribute_summary": variant.attribute_summary,
    }


def serialize_product(product, include_related: bool = False) -> dict:
    payload = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "short_description": product.short_description,
        "description": product.description,
        "price": _money(product.price),
        "compare_at_price": _money(product.compare_at_price),
        "currency": product.currency,
        "stock_quantity": product.stock_quantity,
        "in_stock": product.in_stock,
        "is_active": product.is_active,
        "is_featured": product.is_featured,
        "average_rating": product.average_rating,
        "review_count": product.review_count,
        "category": serialize_category(product.category),
        "brand": serialize_brand(product.brand),
        "vendor": {
            "id": product.vendor.id,
            "business_name": product.vendor.business_name,
            "slug": product.vendor.slug,
            "status": product.vendor.status.value,
        },
        "primary_image": next(
            (serialize_product_image(image) for image in product.images if image.is_primary),
            serialize_product_image(product.images[0]) if product.images else None,
        ),
    }

    if include_related:
        payload["images"] = [serialize_product_image(image) for image in product.images]
        payload["variants"] = [
            serialize_product_variant(variant) for variant in product.variants
        ]

    return payload


def serialize_banner(banner) -> dict:
    return {
        "id": banner.id,
        "title": banner.title,
        "subtitle": banner.subtitle,
        "image_url": banner.image_url,
        "link_url": banner.link_url,
        "placement": banner.placement,
        "sort_order": banner.sort_order,
        "is_active": banner.is_active,
        "starts_at": _iso_datetime(banner.starts_at),
        "ends_at": _iso_datetime(banner.ends_at),
    }


def serialize_flash_sale(flash_sale) -> dict:
    return {
        "id": flash_sale.id,
        "title": flash_sale.title,
        "sale_price": flash_sale.sale_price_amount,
        "starts_at": _iso_datetime(flash_sale.starts_at),
        "ends_at": _iso_datetime(flash_sale.ends_at),
        "is_active": flash_sale.is_active,
        "product": serialize_product(flash_sale.product),
    }
