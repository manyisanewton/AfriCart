from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.products.schemas import (
    serialize_product,
    serialize_product_image,
    serialize_product_variant,
)
from app.blueprints.vendors import vendors_bp
from app.blueprints.vendors.schemas import (
    validate_vendor_bulk_import_payload,
    validate_vendor_image_update_payload,
    validate_stock_payload,
    validate_vendor_product_payload,
    validate_vendor_product_update_payload,
    validate_vendor_variant_payload,
    validate_vendor_variant_update_payload,
)
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import Order, OrderItem, Product, UserRole
from app.services.analytics_service import vendor_summary, vendor_top_products
from app.services.audit_service import log_audit_event
from app.services.catalog_validation_service import (
    ensure_unique_product_slug_and_sku,
    get_active_brand,
    get_active_category,
)
from app.utils.api import get_json_payload, not_found_response
from app.services.vendor_product_service import (
    create_vendor_variant,
    delete_vendor_product,
    delete_vendor_variant,
    get_vendor_product,
    get_vendor_variant,
    list_low_stock_products,
    update_vendor_product,
    update_vendor_product_image,
    update_vendor_variant,
)
from app.services.vendor_operations_service import (
    build_vendor_analytics_report,
    build_vendor_payout_summary,
    export_vendor_catalog,
)
from app.services.vendor_media_service import add_product_image, delete_product_image
from app.services.vendor_dashboard_service import build_vendor_dashboard


def _vendor_profile_or_403():
    vendor = g.current_user.vendor_profile
    if vendor is None:
        return None, (
            jsonify(
                {
                    "error": {
                        "code": "vendor_profile_missing",
                        "message": "Vendor profile is required for this action.",
                    }
                }
            ),
            403,
        )
    return vendor, None


def _vendor_product_or_404(product_id: int, vendor_id: int):
    return Product.query.filter_by(id=product_id, vendor_id=vendor_id).first()


def _add_vendor_audit_log(*, action: str, entity_id: int, metadata: dict | None = None) -> None:
    db.session.add(
        log_audit_event(
            actor_user_id=g.current_user.id,
            action=action,
            entity_type="product",
            entity_id=entity_id,
            metadata=metadata,
        )
    )


@vendors_bp.get("/profile")
@role_required(UserRole.VENDOR.value)
def get_vendor_profile():
    """
    Get the authenticated vendor profile.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor profile details.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    return jsonify(
        {
            "item": {
                "id": vendor.id,
                "business_name": vendor.business_name,
                "slug": vendor.slug,
                "phone_number": vendor.phone_number,
                "support_email": vendor.support_email,
                "description": vendor.description,
                "status": vendor.status.value,
                "is_verified": vendor.is_verified,
                "kyc_status": (
                    vendor.kyc_submission.status.value
                    if vendor.kyc_submission is not None
                    else "not_submitted"
                ),
            }
        }
    )


@vendors_bp.get("/dashboard")
@role_required(UserRole.VENDOR.value)
def get_vendor_dashboard():
    """
    Get the authenticated vendor dashboard summary.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor dashboard summary.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    return jsonify({"item": build_vendor_dashboard(vendor)})


@vendors_bp.get("/products")
@role_required(UserRole.VENDOR.value)
def list_vendor_products():
    """
    List products owned by the authenticated vendor.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor product list.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    products = (
        Product.query.filter_by(vendor_id=vendor.id)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_product(product, include_related=True) for product in products]})


@vendors_bp.get("/products/export")
@role_required(UserRole.VENDOR.value)
def export_products():
    vendor, error = _vendor_profile_or_403()
    if error:
        return error
    return jsonify(export_vendor_catalog(vendor))


@vendors_bp.post("/products/bulk-import")
@role_required(UserRole.VENDOR.value)
def bulk_import_products():
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_bulk_import_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    results = {
        "created_count": 0,
        "updated_count": 0,
        "failed_count": 0,
        "errors": [],
        "items": [],
    }
    for index, item_payload in enumerate(payload["items"]):
        normalized = validate_vendor_product_payload(item_payload)
        if "errors" in normalized:
            results["failed_count"] += 1
            results["errors"].append({"index": index, "details": normalized["errors"]})
            continue

        category, category_error = get_active_category(normalized["category_id"])
        if category_error:
            results["failed_count"] += 1
            results["errors"].append({"index": index, "details": category_error.details})
            continue

        brand, brand_error = get_active_brand(normalized["brand_id"])
        if brand_error:
            results["failed_count"] += 1
            results["errors"].append({"index": index, "details": brand_error.details})
            continue

        existing = (
            Product.query.filter_by(vendor_id=vendor.id, sku=normalized["sku"]).first()
            or Product.query.filter_by(vendor_id=vendor.id, slug=normalized["slug"]).first()
        )
        if existing is not None:
            if not payload["update_existing"]:
                results["failed_count"] += 1
                results["errors"].append(
                    {"index": index, "details": {"product": "Matching product already exists for this vendor."}}
                )
                continue
            existing.category_id = category.id
            existing.brand_id = brand.id
            existing.name = normalized["name"]
            existing.slug = normalized["slug"]
            existing.sku = normalized["sku"]
            existing.price = normalized["price"]
            existing.stock_quantity = normalized["stock_quantity"]
            existing.short_description = normalized["short_description"]
            existing.description = normalized["description"]
            existing.is_active = normalized["is_active"]
            existing.is_featured = normalized["is_featured"]
            product = existing
            results["updated_count"] += 1
            audit_action = "vendor.product_bulk_updated"
        else:
            uniqueness_error = ensure_unique_product_slug_and_sku(
                slug=normalized["slug"],
                sku=normalized["sku"],
            )
            if uniqueness_error:
                results["failed_count"] += 1
                results["errors"].append({"index": index, "details": uniqueness_error.details})
                continue
            product = Product(
                vendor_id=vendor.id,
                category_id=category.id,
                brand_id=brand.id,
                name=normalized["name"],
                slug=normalized["slug"],
                sku=normalized["sku"],
                short_description=normalized["short_description"],
                description=normalized["description"],
                price=normalized["price"],
                stock_quantity=normalized["stock_quantity"],
                is_active=normalized["is_active"],
                is_featured=normalized["is_featured"],
            )
            db.session.add(product)
            db.session.flush()
            results["created_count"] += 1
            audit_action = "vendor.product_bulk_created"

        _add_vendor_audit_log(
            action=audit_action,
            entity_id=product.id,
            metadata={"slug": product.slug, "stock_quantity": product.stock_quantity},
        )
        results["items"].append(serialize_product(product, include_related=True))

    db.session.commit()
    return jsonify(results)


@vendors_bp.get("/products/<int:product_id>")
@role_required(UserRole.VENDOR.value)
def get_vendor_product_detail(product_id: int):
    """
    Get a vendor-owned product detail.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor product detail.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return not_found_response("Product not found.")
    return jsonify({"item": serialize_product(product, include_related=True)})


@vendors_bp.post("/products")
@role_required(UserRole.VENDOR.value)
def create_vendor_product():
    """
    Create a product owned by the authenticated vendor.
    ---
    tags:
      - Vendors
    responses:
      201:
        description: Product created.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_product_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    category, category_error = get_active_category(payload["category_id"])
    if category_error:
        return validation_error(category_error.details)

    brand, brand_error = get_active_brand(payload["brand_id"])
    if brand_error:
        return validation_error(brand_error.details)

    uniqueness_error = ensure_unique_product_slug_and_sku(
        slug=payload["slug"],
        sku=payload["sku"],
    )
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        brand_id=brand.id,
        name=payload["name"],
        slug=payload["slug"],
        sku=payload["sku"],
        short_description=payload["short_description"],
        description=payload["description"],
        price=payload["price"],
        stock_quantity=payload["stock_quantity"],
        is_active=payload["is_active"],
        is_featured=payload["is_featured"],
    )
    db.session.add(product)
    db.session.flush()
    _add_vendor_audit_log(
        action="vendor.product_created",
        entity_id=product.id,
        metadata={"slug": product.slug, "stock_quantity": product.stock_quantity},
    )
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)}), 201


@vendors_bp.patch("/products/<int:product_id>")
@role_required(UserRole.VENDOR.value)
def update_vendor_product_detail(product_id: int):
    """
    Update a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product updated.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_product_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product, service_error = update_vendor_product(
        vendor=vendor,
        product_id=product_id,
        payload=payload,
    )
    if service_error is not None:
        if service_error.status_code == 404:
            return not_found_response("Product not found.")
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_updated",
        entity_id=product.id,
        metadata={"slug": product.slug, "stock_quantity": product.stock_quantity},
    )
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)})


@vendors_bp.patch("/products/<int:product_id>/stock")
@role_required(UserRole.VENDOR.value)
def update_vendor_stock(product_id: int):
    """
    Update stock quantity for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product stock updated.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    product = _vendor_product_or_404(product_id, vendor.id)
    if product is None:
        return not_found_response("Product not found.")

    payload = validate_stock_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product.stock_quantity = payload["stock_quantity"]
    _add_vendor_audit_log(
        action="vendor.product_stock_updated",
        entity_id=product.id,
        metadata={"slug": product.slug, "stock_quantity": product.stock_quantity},
    )
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)})


@vendors_bp.delete("/products/<int:product_id>")
@role_required(UserRole.VENDOR.value)
def remove_vendor_product(product_id: int):
    """
    Delete a vendor-owned product if it has no order history.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product deleted.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    product, service_error = delete_vendor_product(vendor=vendor, product_id=product_id)
    if service_error is not None:
        if service_error.status_code == 404:
            return not_found_response("Product not found.")
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_deleted",
        entity_id=product.id,
        metadata={"slug": product.slug},
    )
    db.session.commit()
    return jsonify({"message": "Product deleted successfully."})


@vendors_bp.get("/products/<int:product_id>/variants")
@role_required(UserRole.VENDOR.value)
def list_vendor_product_variants(product_id: int):
    """
    List variants for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product variant list.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    product = get_vendor_product(vendor_id=vendor.id, product_id=product_id)
    if product is None:
        return not_found_response("Product not found.")
    return jsonify({"items": [serialize_product_variant(variant) for variant in product.variants]})


@vendors_bp.post("/products/<int:product_id>/variants")
@role_required(UserRole.VENDOR.value)
def create_vendor_product_variant(product_id: int):
    """
    Create a variant for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      201:
        description: Product variant created.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_variant_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    variant, service_error = create_vendor_variant(vendor=vendor, product_id=product_id, payload=payload)
    if service_error is not None:
        if service_error.status_code == 404:
            return not_found_response("Product not found.")
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_variant_created",
        entity_id=variant.product_id,
        metadata={"variant_id": variant.id, "sku": variant.sku},
    )
    db.session.commit()
    return jsonify({"item": serialize_product_variant(variant)}), 201


@vendors_bp.patch("/products/<int:product_id>/variants/<int:variant_id>")
@role_required(UserRole.VENDOR.value)
def update_vendor_product_variant(product_id: int, variant_id: int):
    """
    Update a variant for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product variant updated.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_variant_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    variant, service_error = update_vendor_variant(
        vendor=vendor,
        product_id=product_id,
        variant_id=variant_id,
        payload=payload,
    )
    if service_error is not None:
        if service_error.status_code == 404:
            return not_found_response("Variant not found.")
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_variant_updated",
        entity_id=variant.product_id,
        metadata={"variant_id": variant.id, "sku": variant.sku},
    )
    db.session.commit()
    return jsonify({"item": serialize_product_variant(variant)})


@vendors_bp.delete("/products/<int:product_id>/variants/<int:variant_id>")
@role_required(UserRole.VENDOR.value)
def remove_vendor_product_variant(product_id: int, variant_id: int):
    """
    Delete a variant for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product variant deleted.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    variant, service_error = delete_vendor_variant(
        vendor=vendor,
        product_id=product_id,
        variant_id=variant_id,
    )
    if service_error is not None:
        return not_found_response("Variant not found.")

    _add_vendor_audit_log(
        action="vendor.product_variant_deleted",
        entity_id=variant.product_id,
        metadata={"variant_id": variant.id, "sku": variant.sku},
    )
    db.session.commit()
    return jsonify({"message": "Product variant deleted successfully."})


@vendors_bp.post("/products/<int:product_id>/images")
@role_required(UserRole.VENDOR.value)
def upload_vendor_product_image(product_id: int):
    """
    Upload a product image for a vendor-owned product.
    ---
    tags:
      - Vendors
    consumes:
      - multipart/form-data
    responses:
      201:
        description: Product image uploaded.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    sort_order_raw = request.form.get("sort_order", "0")
    try:
        sort_order = int(sort_order_raw)
    except (TypeError, ValueError):
        return validation_error({"sort_order": "sort_order must be an integer."})

    image, service_error = add_product_image(
        vendor=vendor,
        product_id=product_id,
        upload=request.files.get("file"),
        alt_text=str(request.form.get("alt_text") or "").strip() or None,
        is_primary=str(request.form.get("is_primary", "false")).lower() == "true",
        sort_order=sort_order,
    )
    if service_error is not None:
        if service_error.status_code == 404:
            return not_found_response("Product not found.")
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_image_uploaded",
        entity_id=product_id,
        metadata={"image_id": image.id, "is_primary": image.is_primary},
    )
    db.session.commit()
    return jsonify({"item": serialize_product_image(image)}), 201


@vendors_bp.patch("/products/<int:product_id>/images/<int:image_id>")
@role_required(UserRole.VENDOR.value)
def update_vendor_product_image_detail(product_id: int, image_id: int):
    """
    Update metadata for a vendor-owned product image.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product image updated.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    payload = validate_vendor_image_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    image, service_error = update_vendor_product_image(
        vendor=vendor,
        product_id=product_id,
        image_id=image_id,
        payload=payload,
    )
    if service_error is not None:
        if service_error.status_code == 404:
            message = "Product not found." if "product" in service_error.details else "Image not found."
            return not_found_response(message)
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_image_updated",
        entity_id=product_id,
        metadata={"image_id": image.id, "is_primary": image.is_primary, "sort_order": image.sort_order},
    )
    db.session.commit()
    return jsonify({"item": serialize_product_image(image)})


@vendors_bp.delete("/products/<int:product_id>/images/<int:image_id>")
@role_required(UserRole.VENDOR.value)
def remove_vendor_product_image(product_id: int, image_id: int):
    """
    Delete a product image for a vendor-owned product.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Product image deleted.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    image, service_error = delete_product_image(
        vendor=vendor,
        product_id=product_id,
        image_id=image_id,
    )
    if service_error is not None:
        if service_error.status_code == 404:
            message = "Product not found." if "product" in service_error.details else "Image not found."
            return not_found_response(message)
        return validation_error(service_error.details)

    _add_vendor_audit_log(
        action="vendor.product_image_deleted",
        entity_id=product_id,
        metadata={"image_id": image_id},
    )
    db.session.commit()
    return jsonify({"message": "Product image deleted successfully."})


@vendors_bp.get("/orders")
@role_required(UserRole.VENDOR.value)
def list_vendor_orders():
    """
    List orders that contain products owned by the authenticated vendor.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor order list.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    orders = (
        Order.query.join(OrderItem, Order.items)
        .join(Product, OrderItem.product)
        .filter(Product.vendor_id == vendor.id)
        .distinct()
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )
    return jsonify(
        {"items": [serialize_order(order, include_items=True) for order in orders]}
    )


@vendors_bp.get("/inventory/low-stock")
@role_required(UserRole.VENDOR.value)
def list_vendor_low_stock_products():
    """
    List vendor products at or below a stock threshold.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Low stock product list.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error

    threshold_raw = request.args.get("threshold", "5")
    try:
        threshold = int(threshold_raw)
        if threshold < 0:
            raise ValueError
    except (TypeError, ValueError):
        return validation_error({"threshold": "threshold must be a non-negative integer."})

    products = list_low_stock_products(vendor=vendor, threshold=threshold)
    return jsonify(
        {
            "items": [serialize_product(product, include_related=True) for product in products],
            "summary": {"threshold": threshold, "count": len(products)},
        }
    )


@vendors_bp.get("/analytics/summary")
@role_required(UserRole.VENDOR.value)
def get_vendor_summary():
    """
    Get summary analytics for the authenticated vendor.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor summary analytics.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error
    return jsonify({"item": vendor_summary(vendor.id)})


@vendors_bp.get("/analytics/report")
@role_required(UserRole.VENDOR.value)
def get_vendor_analytics_report():
    vendor, error = _vendor_profile_or_403()
    if error:
        return error
    return jsonify({"item": build_vendor_analytics_report(vendor)})


@vendors_bp.get("/analytics/top-products")
@role_required(UserRole.VENDOR.value)
def get_vendor_top_products():
    """
    Get top-selling products for the authenticated vendor.
    ---
    tags:
      - Vendors
    responses:
      200:
        description: Vendor top products.
    """
    vendor, error = _vendor_profile_or_403()
    if error:
        return error
    return jsonify({"items": vendor_top_products(vendor.id)})


@vendors_bp.get("/payouts/summary")
@role_required(UserRole.VENDOR.value)
def get_vendor_payout_summary():
    vendor, error = _vendor_profile_or_403()
    if error:
        return error
    return jsonify({"item": build_vendor_payout_summary(vendor)})
