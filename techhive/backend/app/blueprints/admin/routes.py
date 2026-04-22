from flask import jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.admin import admin_bp
from app.blueprints.admin.schemas import (
    validate_named_entity_payload,
    validate_order_status_payload,
    validate_product_active_payload,
    validate_role_payload,
    validate_vendor_status_payload,
)
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.products.schemas import serialize_brand, serialize_category, serialize_product
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import Brand, Category, Order, OrderStatus, Product, User, UserRole, Vendor, VendorStatus


def _not_found(message: str):
    return jsonify({"error": {"code": "not_found", "message": message}}), 404


@admin_bp.get("/users")
@role_required(UserRole.ADMIN.value)
def list_users():
    """
    List all users for admin management.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Users list.
    """
    users = User.query.order_by(User.created_at.desc(), User.id.desc()).all()
    return jsonify(
        {
            "items": [
                {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "role": user.role.value,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                }
                for user in users
            ]
        }
    )


@admin_bp.patch("/users/<int:user_id>/role")
@role_required(UserRole.ADMIN.value)
def update_user_role(user_id: int):
    """
    Update a user's role.
    ---
    tags:
      - Admin
    responses:
      200:
        description: User role updated.
    """
    payload = validate_role_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = db.session.get(User, user_id)
    if user is None:
        return _not_found("User not found.")

    user.role = UserRole(payload["role"])
    db.session.commit()
    return jsonify(
        {
            "item": {
                "id": user.id,
                "email": user.email,
                "role": user.role.value,
            }
        }
    )


@admin_bp.get("/vendors")
@role_required(UserRole.ADMIN.value)
def list_vendors():
    """
    List vendor accounts for approval and review.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Vendor list.
    """
    vendors = Vendor.query.order_by(Vendor.created_at.desc(), Vendor.id.desc()).all()
    return jsonify(
        {
            "items": [
                {
                    "id": vendor.id,
                    "business_name": vendor.business_name,
                    "slug": vendor.slug,
                    "status": vendor.status.value,
                    "is_verified": vendor.is_verified,
                    "user_id": vendor.user_id,
                }
                for vendor in vendors
            ]
        }
    )


@admin_bp.patch("/vendors/<int:vendor_id>/status")
@role_required(UserRole.ADMIN.value)
def update_vendor_status(vendor_id: int):
    """
    Approve, suspend, or reject a vendor.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Vendor status updated.
    """
    payload = validate_vendor_status_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return _not_found("Vendor not found.")

    vendor.status = VendorStatus(payload["status"])
    vendor.is_verified = vendor.status == VendorStatus.APPROVED
    db.session.commit()
    return jsonify(
        {
            "item": {
                "id": vendor.id,
                "business_name": vendor.business_name,
                "status": vendor.status.value,
                "is_verified": vendor.is_verified,
            }
        }
    )


@admin_bp.post("/categories")
@role_required(UserRole.ADMIN.value)
def create_category():
    """
    Create a new category.
    ---
    tags:
      - Admin
    responses:
      201:
        description: Category created.
    """
    payload = validate_named_entity_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    if Category.query.filter_by(slug=payload["slug"]).first():
        return validation_error({"slug": "A category with that slug already exists."})

    category = Category(
        name=payload["name"],
        slug=payload["slug"],
        description=payload["description"],
    )
    db.session.add(category)
    db.session.commit()
    return jsonify({"item": serialize_category(category)}), 201


@admin_bp.post("/brands")
@role_required(UserRole.ADMIN.value)
def create_brand():
    """
    Create a new brand.
    ---
    tags:
      - Admin
    responses:
      201:
        description: Brand created.
    """
    payload = validate_named_entity_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    if Brand.query.filter_by(slug=payload["slug"]).first():
        return validation_error({"slug": "A brand with that slug already exists."})

    brand = Brand(
        name=payload["name"],
        slug=payload["slug"],
        description=payload["description"],
        website_url=payload["website_url"],
        logo_url=payload["logo_url"],
    )
    db.session.add(brand)
    db.session.commit()
    return jsonify({"item": serialize_brand(brand)}), 201


@admin_bp.get("/products")
@role_required(UserRole.ADMIN.value)
def list_products():
    """
    List all products for moderation.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Product moderation list.
    """
    products = Product.query.order_by(Product.created_at.desc(), Product.id.desc()).all()
    return jsonify({"items": [serialize_product(product, include_related=True) for product in products]})


@admin_bp.patch("/products/<int:product_id>/active")
@role_required(UserRole.ADMIN.value)
def update_product_active_state(product_id: int):
    """
    Activate or deactivate a product.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Product moderation state updated.
    """
    payload = validate_product_active_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    product.is_active = payload["is_active"]
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)})


@admin_bp.get("/orders")
@role_required(UserRole.ADMIN.value)
def list_orders():
    """
    List all marketplace orders for admin oversight.
    ---
    tags:
      - Admin
    responses:
      200:
        description: All orders.
    """
    orders = Order.query.order_by(Order.created_at.desc(), Order.id.desc()).all()
    return jsonify({"items": [serialize_order(order, include_items=True) for order in orders]})


@admin_bp.patch("/orders/<int:order_id>/status")
@role_required(UserRole.ADMIN.value)
def update_order_status(order_id: int):
    """
    Update an order status.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Order status updated.
    """
    payload = validate_order_status_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    order = db.session.get(Order, order_id)
    if order is None:
        return _not_found("Order not found.")

    order.status = OrderStatus(payload["status"])
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})
