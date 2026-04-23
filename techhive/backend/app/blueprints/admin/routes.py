from datetime import datetime, timezone

from flask import current_app, g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.admin import admin_bp
from app.blueprints.admin.schemas import (
    validate_banner_payload,
    validate_flash_sale_payload,
    validate_named_entity_payload,
    validate_order_status_payload,
    validate_promo_code_payload,
    validate_refund_status_payload,
    validate_product_active_payload,
    validate_role_payload,
    validate_vendor_kyc_status_payload,
    validate_vendor_status_payload,
)
from app.blueprints.orders.helpers import serialize_order, serialize_refund
from app.blueprints.promotions.helpers import serialize_promo_code
from app.blueprints.products.schemas import (
    serialize_banner,
    serialize_brand,
    serialize_category,
    serialize_flash_sale,
    serialize_product,
)
from app.blueprints.payments.helpers import serialize_payment
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import (
    AuditLog,
    Banner,
    Brand,
    Category,
    FlashSale,
    Order,
    OrderStatus,
    Product,
    PromoCode,
    PromoCodeType,
    Refund,
    RefundStatus,
    User,
    UserRole,
    Vendor,
    VendorKYCStatus,
    VendorKYCSubmission,
    VendorStatus,
)
from app.services.audit_service import log_audit_event, serialize_audit_log
from app.services.payment_reconciliation_service import reconcile_stale_mpesa_payments
from app.blueprints.vendors.schemas import serialize_vendor_kyc_submission


def _not_found(message: str):
    return jsonify({"error": {"code": "not_found", "message": message}}), 404


def _add_audit_log(*, action: str, entity_type: str, entity_id: int, metadata: dict | None = None) -> None:
    db.session.add(
        log_audit_event(
            actor_user_id=g.current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
    )


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
    _add_audit_log(
        action="admin.user_role_updated",
        entity_type="user",
        entity_id=user.id,
        metadata={"role": user.role.value, "email": user.email},
    )
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
    _add_audit_log(
        action="admin.vendor_status_updated",
        entity_type="vendor",
        entity_id=vendor.id,
        metadata={"status": vendor.status.value, "business_name": vendor.business_name},
    )
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


@admin_bp.get("/kyc-submissions")
@role_required(UserRole.ADMIN.value)
def list_vendor_kyc_submissions():
    """
    List vendor KYC submissions.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Vendor KYC submissions list.
    """
    submissions = (
        VendorKYCSubmission.query.order_by(
            VendorKYCSubmission.submitted_at.desc(),
            VendorKYCSubmission.id.desc(),
        ).all()
    )
    return jsonify({"items": [serialize_vendor_kyc_submission(submission) for submission in submissions]})


@admin_bp.patch("/kyc-submissions/<int:submission_id>/status")
@role_required(UserRole.ADMIN.value)
def update_vendor_kyc_status(submission_id: int):
    """
    Review and update vendor KYC status.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Vendor KYC status updated.
    """
    payload = validate_vendor_kyc_status_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    submission = db.session.get(VendorKYCSubmission, submission_id)
    if submission is None:
        return _not_found("KYC submission not found.")

    submission.status = VendorKYCStatus(payload["status"])
    submission.admin_note = payload["admin_note"]
    submission.reviewed_at = datetime.now(timezone.utc)
    _add_audit_log(
        action="admin.vendor_kyc_status_updated",
        entity_type="vendor_kyc_submission",
        entity_id=submission.id,
        metadata={"status": submission.status.value, "vendor_id": submission.vendor_id},
    )
    db.session.commit()
    return jsonify({"item": serialize_vendor_kyc_submission(submission)})


@admin_bp.post("/payments/reconcile-stale")
@role_required(UserRole.ADMIN.value)
def reconcile_stale_payments():
    """
    Reconcile stale pending M-Pesa payments that missed their callback window.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Stale payments reconciled.
    """
    payload = request.get_json(silent=True) or {}
    limit = payload.get("limit", current_app.config["MPESA_RECONCILIATION_BATCH_LIMIT"])

    try:
        limit = int(limit)
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return validation_error({"limit": "limit must be a positive integer."})

    results = reconcile_stale_mpesa_payments(
        limit=limit,
        max_attempts=current_app.config["MPESA_RECONCILIATION_MAX_ATTEMPTS"],
        retry_delay_minutes=current_app.config["MPESA_RECONCILIATION_RETRY_DELAY_MINUTES"],
    )
    payments = (
        results["awaiting_confirmation"]
        + results["provider_failed"]
        + results["manual_review"]
        + results["timed_out"]
    )
    for payment in payments:
        _add_audit_log(
            action="admin.payment_reconciled",
            entity_type="payment",
            entity_id=payment.id,
            metadata={"reference": payment.reference, "failure_code": payment.failure_code},
        )
    db.session.commit()
    return jsonify(
        {
            "count": len(payments),
            "awaiting_confirmation_count": len(results["awaiting_confirmation"]),
            "provider_failed_count": len(results["provider_failed"]),
            "manual_review_count": len(results["manual_review"]),
            "timed_out_count": len(results["timed_out"]),
            "items": [serialize_payment(payment) for payment in payments],
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
    db.session.flush()
    _add_audit_log(
        action="admin.category_created",
        entity_type="category",
        entity_id=category.id,
        metadata={"name": category.name, "slug": category.slug},
    )
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
    db.session.flush()
    _add_audit_log(
        action="admin.brand_created",
        entity_type="brand",
        entity_id=brand.id,
        metadata={"name": brand.name, "slug": brand.slug},
    )
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
    _add_audit_log(
        action="admin.product_active_updated",
        entity_type="product",
        entity_id=product.id,
        metadata={"is_active": product.is_active, "slug": product.slug},
    )
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


@admin_bp.get("/promo-codes")
@role_required(UserRole.ADMIN.value)
def list_promo_codes():
    """
    List promo codes.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Promo codes list.
    """
    promo_codes = PromoCode.query.order_by(PromoCode.created_at.desc(), PromoCode.id.desc()).all()
    return jsonify({"items": [serialize_promo_code(promo_code) for promo_code in promo_codes]})


@admin_bp.get("/audit-logs")
@role_required(UserRole.ADMIN.value)
def list_audit_logs():
    """
    List audit logs.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Audit log list.
    """
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()
    return jsonify({"items": [serialize_audit_log(audit_log) for audit_log in audit_logs]})


@admin_bp.get("/banners")
@role_required(UserRole.ADMIN.value)
def list_banners():
    """
    List banners.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Banner list.
    """
    banners = Banner.query.order_by(Banner.sort_order.asc(), Banner.id.desc()).all()
    return jsonify({"items": [serialize_banner(banner) for banner in banners]})


@admin_bp.post("/banners")
@role_required(UserRole.ADMIN.value)
def create_banner():
    """
    Create a banner.
    ---
    tags:
      - Admin
    responses:
      201:
        description: Banner created.
    """
    payload = validate_banner_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    banner = Banner(
        title=payload["title"],
        subtitle=payload["subtitle"],
        image_url=payload["image_url"],
        link_url=payload["link_url"],
        placement=payload["placement"],
        sort_order=payload["sort_order"],
        is_active=payload["is_active"],
    )
    db.session.add(banner)
    db.session.flush()
    _add_audit_log(
        action="admin.banner_created",
        entity_type="banner",
        entity_id=banner.id,
        metadata={"title": banner.title, "placement": banner.placement},
    )
    db.session.commit()
    return jsonify({"item": serialize_banner(banner)}), 201


@admin_bp.post("/promo-codes")
@role_required(UserRole.ADMIN.value)
def create_promo_code():
    """
    Create a promo code.
    ---
    tags:
      - Admin
    responses:
      201:
        description: Promo code created.
    """
    payload = validate_promo_code_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    if PromoCode.query.filter_by(code=payload["code"]).first():
        return validation_error({"code": "A promo code with that code already exists."})

    promo_code = PromoCode(
        code=payload["code"],
        discount_type=PromoCodeType(payload["discount_type"]),
        discount_value=payload["discount_value"],
        minimum_order_amount=payload["minimum_order_amount"],
        is_active=payload["is_active"],
    )
    db.session.add(promo_code)
    db.session.flush()
    _add_audit_log(
        action="admin.promo_code_created",
        entity_type="promo_code",
        entity_id=promo_code.id,
        metadata={"code": promo_code.code, "discount_type": promo_code.discount_type.value},
    )
    db.session.commit()
    return jsonify({"item": serialize_promo_code(promo_code)}), 201


@admin_bp.get("/flash-sales")
@role_required(UserRole.ADMIN.value)
def list_flash_sales():
    """
    List flash sales.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Flash sale list.
    """
    flash_sales = FlashSale.query.order_by(FlashSale.ends_at.asc(), FlashSale.id.desc()).all()
    return jsonify({"items": [serialize_flash_sale(flash_sale) for flash_sale in flash_sales]})


@admin_bp.post("/flash-sales")
@role_required(UserRole.ADMIN.value)
def create_flash_sale():
    """
    Create a flash sale.
    ---
    tags:
      - Admin
    responses:
      201:
        description: Flash sale created.
    """
    payload = validate_flash_sale_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = db.session.get(Product, payload["product_id"])
    if product is None:
        return validation_error({"product_id": "Selected product was not found."})

    flash_sale = FlashSale(
        product_id=product.id,
        title=payload["title"],
        sale_price=payload["sale_price"],
        starts_at=payload["starts_at"],
        ends_at=payload["ends_at"],
        is_active=payload["is_active"],
    )
    db.session.add(flash_sale)
    db.session.flush()
    _add_audit_log(
        action="admin.flash_sale_created",
        entity_type="flash_sale",
        entity_id=flash_sale.id,
        metadata={"title": flash_sale.title, "product_id": product.id},
    )
    db.session.commit()
    return jsonify({"item": serialize_flash_sale(flash_sale)}), 201


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
    _add_audit_log(
        action="admin.order_status_updated",
        entity_type="order",
        entity_id=order.id,
        metadata={"status": order.status.value, "order_number": order.order_number},
    )
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})


@admin_bp.get("/refunds")
@role_required(UserRole.ADMIN.value)
def list_refunds():
    """
    List refund requests.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Refund requests list.
    """
    refunds = Refund.query.order_by(Refund.requested_at.desc(), Refund.id.desc()).all()
    return jsonify({"items": [serialize_refund(refund) for refund in refunds]})


@admin_bp.patch("/refunds/<int:refund_id>/status")
@role_required(UserRole.ADMIN.value)
def update_refund_status(refund_id: int):
    """
    Update a refund request status.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Refund status updated.
    """
    payload = validate_refund_status_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    refund = db.session.get(Refund, refund_id)
    if refund is None:
        return _not_found("Refund not found.")

    refund.status = RefundStatus(payload["status"])
    refund.admin_note = payload["admin_note"]
    if refund.status == RefundStatus.PROCESSED:
        refund.processed_at = datetime.now(timezone.utc)
    _add_audit_log(
        action="admin.refund_status_updated",
        entity_type="refund",
        entity_id=refund.id,
        metadata={"status": refund.status.value, "order_id": refund.order_id},
    )
    db.session.commit()
    return jsonify({"item": serialize_refund(refund)})
