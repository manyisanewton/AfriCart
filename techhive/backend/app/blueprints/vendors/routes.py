from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.products.schemas import serialize_product
from app.blueprints.vendors import vendors_bp
from app.blueprints.vendors.schemas import (
    validate_stock_payload,
    validate_vendor_product_payload,
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
