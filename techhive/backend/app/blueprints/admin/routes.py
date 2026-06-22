from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g, jsonify, request
from sqlalchemy import or_

from app.blueprints.auth.helpers import validation_error
from app.blueprints.admin import admin_bp
from app.blueprints.admin.schemas import (
    validate_admin_user_create_payload,
    validate_admin_order_update_payload,
    validate_delivery_zone_payload,
    validate_delivery_zone_update_payload,
    validate_admin_product_payload,
    validate_admin_product_update_payload,
    validate_banner_payload,
    validate_banner_update_payload,
    validate_bulk_email_payload,
    validate_bulk_notification_payload,
    validate_flash_sale_payload,
    validate_flash_sale_update_payload,
    validate_cms_page_payload,
    validate_cms_page_update_payload,
    validate_integration_connection_payload,
    validate_integration_connection_update_payload,
    validate_named_entity_payload,
    validate_named_entity_update_payload,
    validate_notification_delivery_retry_payload,
    validate_offer_component_payload,
    validate_offer_component_update_payload,
    validate_offer_payload,
    validate_offer_status_payload,
    validate_offer_update_payload,
    validate_order_status_payload,
    validate_partner_payload,
    validate_partner_update_payload,
    validate_platform_setting_payload,
    validate_platform_setting_update_payload,
    validate_recommendation_settings_update_payload,
    validate_promo_code_payload,
    validate_promo_code_update_payload,
    validate_refund_status_payload,
    validate_product_active_payload,
    validate_product_attribute_payload,
    validate_product_attribute_update_payload,
    validate_product_option_payload,
    validate_product_option_update_payload,
    validate_range_payload,
    validate_range_product_payload,
    validate_range_update_payload,
    validate_product_type_payload,
    validate_product_type_update_payload,
    validate_voucher_offer_payload,
    validate_voucher_payload,
    validate_voucher_update_payload,
    validate_role_payload,
    validate_admin_review_update_payload,
    validate_stock_alert_status_payload,
    validate_support_ticket_status_payload,
    validate_supplier_create_payload,
    validate_supplier_update_payload,
    validate_user_active_payload,
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
    serialize_product_image,
    serialize_product,
)
from app.blueprints.payments.helpers import serialize_payment
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import (
    Address,
    AuditLog,
    Banner,
    Brand,
    Category,
    CmsPage,
    DeliveryAgent,
    DeliveryZone,
    FlashSale,
    IntegrationConnection,
    IntegrationLog,
    NotificationChannel,
    NotificationType,
    Offer,
    OfferBenefit,
    OfferCondition,
    Order,
    OrderItem,
    OrderStatus,
    Partner,
    NotificationDelivery,
    NotificationDeliveryStatus,
    PlatformSetting,
    Product,
    ProductAttribute,
    ProductImage,
    ProductOption,
    ProductRange,
    ProductStockAlert,
    ProductType,
    PromoCode,
    PromoCodeType,
    Review,
    Refund,
    RefundStatus,
    SupportTicket,
    SupportTicketStatus,
    Supplier,
    SupplierStatus,
    User,
    UserRole,
    Vendor,
    VendorKYCStatus,
    VendorKYCSubmission,
    VendorStatus,
)
from app.services.audit_service import log_audit_event, serialize_audit_log
from app.services.admin_resource_service import (
    delete_banner,
    delete_brand,
    delete_category,
    delete_flash_sale,
    delete_promo_code,
    update_banner,
    update_brand,
    update_category,
    update_flash_sale,
    update_promo_code,
    update_user_active,
)
from app.services.admin_dashboard_service import build_admin_dashboard
from app.services.admin_reporting_service import (
    build_admin_operations_queues,
    build_admin_overview_report,
    list_vendor_performance,
)
from app.services.bulk_email_service import dispatch_bulk_email_campaign
from app.services.campaign_summary_service import build_campaign_summary
from app.services.integration_service import (
    append_integration_log,
    get_connection_adapter,
    get_connection_payload,
    list_all_connections,
    serialize_integration_connection,
)
from app.services.notification_dispatch_service import dispatch_bulk_notification
from app.services.notification_dispatch_service import retry_notification_delivery
from app.services.major_notification_service import (
    notify_refund_updated,
    notify_support_ticket_updated,
)
from app.services.recommendation_analytics_service import summarize_recommendation_metrics
from app.services.recommendation_settings_service import (
    RECOMMENDATION_SETTING_KEYS,
    serialize_recommendation_settings,
)
from app.services.catalog_validation_service import (
    ensure_unique_brand_slug,
    ensure_unique_category_slug,
    ensure_unique_product_slug_and_sku,
    ensure_unique_product_slug_and_sku_for_update,
    ensure_unique_promo_code,
    get_active_brand,
    get_active_category,
    get_product_for_flash_sale,
)
from app.services.commerce_state_service import transition_order
from app.services.payment_reconciliation_service import reconcile_stale_mpesa_payments
from app.services.mpesa_logging_service import tail_mpesa_logs
from app.services.storage_service import IMAGE_EXTENSIONS, delete_stored_file, save_uploaded_file
from app.utils.api import get_json_payload, not_found_response, parse_positive_int
from app.blueprints.notifications.schemas import serialize_notification_delivery
from app.blueprints.support.schemas import serialize_support_ticket
from app.blueprints.vendors.schemas import serialize_vendor_kyc_submission
from app.services.email_service import send_email
from app.utils.security import generate_temporary_password, hash_password


def _not_found(message: str):
    return not_found_response(message)


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


def _serialize_media_asset(image: ProductImage) -> dict:
    filename = Path(image.image_url).name if image.image_url else f"image-{image.id}"
    return {
        "id": image.id,
        "name": filename,
        "url": image.image_url,
        "alt": image.alt_text or "",
        "product_id": image.product_id,
        "product_title": image.product.name if image.product else "",
        "display_order": image.sort_order,
        "created_at": image.created_at.isoformat() if image.created_at else None,
        "is_primary": image.is_primary,
    }


def _serialize_product_type(product_type: ProductType) -> dict:
    return {
        "id": product_type.id,
        "name": product_type.name,
        "slug": product_type.slug,
        "requires_shipping": product_type.requires_shipping,
        "track_stock": product_type.track_stock,
        "is_active": product_type.is_active,
    }


def _serialize_product_attribute(attribute: ProductAttribute) -> dict:
    return {
        "id": attribute.id,
        "product_type_id": attribute.product_type_id,
        "product_class_id": attribute.product_type_id,
        "name": attribute.name,
        "code": attribute.code,
        "type": attribute.type,
        "required": attribute.required,
        "option_group_id": attribute.option_group_id,
    }


def _serialize_product_option(option: ProductOption) -> dict:
    return {
        "id": option.id,
        "name": option.name,
        "code": option.code,
        "type": option.type,
        "required": option.required,
        "help_text": option.help_text or "",
        "order": option.sort_order,
    }


def _humanize_offer_component_type(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw.replace("_", " ").replace("-", " ").title()


def _build_offer_component_text(component_type: str | None, value, range_id: int | None) -> tuple[str, str]:
    label = _humanize_offer_component_type(component_type) or "Component"
    detail_parts = []
    if value not in (None, ""):
        detail_parts.append(str(value))
    if range_id:
        detail_parts.append(f"Range #{range_id}")

    if detail_parts:
        description = f"{label}: {' · '.join(detail_parts)}"
    else:
        description = label
    return label, description


def _serialize_offer_condition(condition: OfferCondition) -> dict:
    name, description = _build_offer_component_text(condition.type, condition.value, condition.range_id)
    return {
        "id": condition.id,
        "type": condition.type,
        "range_id": condition.range_id,
        "range_name": f"Range #{condition.range_id}" if condition.range_id else "",
        "value": condition.value,
        "proxy_class": condition.proxy_class or "",
        "name": name,
        "description": description,
    }


def _serialize_offer_benefit(benefit: OfferBenefit) -> dict:
    name, description = _build_offer_component_text(benefit.type, benefit.value, benefit.range_id)
    if benefit.max_affected_items:
        description = f"{description} · Max {benefit.max_affected_items}"
    return {
        "id": benefit.id,
        "type": benefit.type,
        "range_id": benefit.range_id,
        "range_name": f"Range #{benefit.range_id}" if benefit.range_id else "",
        "value": benefit.value,
        "proxy_class": benefit.proxy_class or "",
        "name": name,
        "description": description,
        "max_affected_items": benefit.max_affected_items,
    }


def _serialize_offer(offer: Offer) -> dict:
    return {
        "id": offer.id,
        "name": offer.name,
        "slug": offer.slug,
        "description": offer.description or "",
        "offer_type": offer.offer_type,
        "exclusive": offer.exclusive,
        "status": offer.status,
        "priority": offer.priority,
        "start_datetime": offer.start_datetime.isoformat() if offer.start_datetime else None,
        "end_datetime": offer.end_datetime.isoformat() if offer.end_datetime else None,
        "num_applications": offer.num_applications or 0,
        "num_orders": offer.num_orders or 0,
        "total_discount": f"{offer.total_discount:.2f}",
        "condition_id": offer.condition_id,
        "benefit_id": offer.benefit_id,
        "condition": _serialize_offer_condition(offer.condition) if offer.condition else None,
        "benefit": _serialize_offer_benefit(offer.benefit) if offer.benefit else None,
        "voucher_ids": [],
    }


def _serialize_voucher(promo_code: PromoCode) -> dict:
    return {
        "id": promo_code.id,
        "name": promo_code.name,
        "code": promo_code.code,
        "usage": promo_code.usage,
        "start_datetime": promo_code.starts_at.isoformat() if promo_code.starts_at else None,
        "end_datetime": promo_code.ends_at.isoformat() if promo_code.ends_at else None,
        "num_basket_additions": 0,
        "num_orders": 0,
        "total_discount": "0.00",
        "date_created": promo_code.created_at.isoformat() if promo_code.created_at else None,
        "offers": [_serialize_offer(offer) for offer in promo_code.offers],
    }


def _serialize_range_item(product_range: ProductRange) -> dict:
    num_products = Product.query.count() if product_range.includes_all_products else len(product_range.products)
    return {
        "id": product_range.id,
        "name": product_range.name,
        "slug": product_range.slug,
        "description": product_range.description or "",
        "is_public": product_range.is_public,
        "includes_all_products": product_range.includes_all_products,
        "num_products": num_products,
    }


def _serialize_range_product(product: Product) -> dict:
    return {
        "id": product.id,
        "title": product.name,
        "upc": product.sku,
    }


def _serialize_delivery_zone(zone: DeliveryZone) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "city": zone.city,
        "fee": zone.fee_amount,
        "estimated_days_min": zone.estimated_days_min,
        "estimated_days_max": zone.estimated_days_max,
        "is_active": zone.is_active,
        "created_at": zone.created_at.isoformat() if zone.created_at else None,
    }


def _serialize_partner(partner: Partner) -> dict:
    return {
        "id": partner.id,
        "name": partner.name,
        "code": partner.code or "",
        "user_count": len(partner.users),
    }


def _serialize_partner_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.full_name or user.email,
    }


def _serialize_supplier_partner(partner: Partner | None) -> dict:
    if partner is None:
        return {"id": 0, "name": "", "code": ""}
    return {
        "id": partner.id,
        "name": partner.name,
        "code": partner.code or "",
    }


def _serialize_supplier_user(user: User | None) -> dict:
    if user is None:
        return {
            "id": 0,
            "email": "",
            "username": "",
            "first_name": "",
            "last_name": "",
            "is_active": False,
        }
    return {
        "id": user.id,
        "email": user.email,
        "username": user.full_name or user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
    }


def _serialize_supplier(supplier: Supplier) -> dict:
    return {
        "id": supplier.id,
        "status": supplier.status.value if hasattr(supplier.status, "value") else supplier.status,
        "company_name": supplier.company_name,
        "contact_name": supplier.contact_name or "",
        "phone": supplier.phone or "",
        "country_code": supplier.country_code or "",
        "website": supplier.website or "",
        "notes": supplier.notes or "",
        "partner": _serialize_supplier_partner(supplier.partner),
        "user": _serialize_supplier_user(supplier.user),
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
        "updated_at": supplier.updated_at.isoformat() if supplier.updated_at else None,
    }


def _serialize_stock_alert(alert: ProductStockAlert) -> dict:
    product = alert.product
    return {
        "id": alert.id,
        "status": alert.status,
        "threshold": alert.threshold,
        "date_created": alert.created_at.isoformat() if alert.created_at else None,
        "date_closed": alert.closed_at.isoformat() if alert.closed_at else None,
        "stockrecord": {
            "id": product.id if product else None,
            "partner_sku": product.sku if product else "",
            "num_in_stock": product.stock_quantity if product else 0,
            "product_id": product.id if product else None,
            "product_title": product.name if product else "",
        },
    }


def _serialize_admin_review(review: Review) -> dict:
    return {
        "id": review.id,
        "product_id": review.product_id,
        "product_title": review.product.name if review.product else "",
        "score": review.rating,
        "title": review.title or "",
        "body": review.comment,
        "user_id": review.user_id,
        "name": review.user.full_name if review.user else "",
        "email": review.user.email if review.user else "",
        "status": review.status,
        "date_created": review.created_at.isoformat() if review.created_at else None,
    }


def _ensure_stock_alerts_for_low_stock_products() -> None:
    products = Product.query.filter(Product.stock_quantity <= Product.low_stock_threshold).all()
    existing_by_product_id = {
        alert.product_id: alert
        for alert in ProductStockAlert.query.all()
    }
    changed = False

    for product in products:
        alert = existing_by_product_id.get(product.id)
        if alert is None:
            db.session.add(
                ProductStockAlert(
                    product_id=product.id,
                    threshold=product.low_stock_threshold,
                    status="open",
                )
            )
            changed = True
        else:
            if alert.threshold != product.low_stock_threshold:
                alert.threshold = product.low_stock_threshold
                changed = True

    if changed:
        db.session.commit()


def _serialize_user_brief(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "role": user.role.value,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _serialize_delivery_agent_brief(agent: DeliveryAgent) -> dict:
    active_assignments = Order.query.filter_by(delivery_agent_id=agent.id).count()
    return {
        "id": agent.id,
        "display_name": agent.display_name,
        "phone_number": agent.phone_number,
        "is_active": agent.is_active,
        "active_assignments": active_assignments,
    }


def _serialize_address_brief(address: Address) -> dict:
    return {
        "id": address.id,
        "label": address.label,
        "recipient_name": address.recipient_name,
        "phone_number": address.phone_number,
        "country": address.country,
        "city": address.city,
        "state_or_county": address.state_or_county,
        "postal_code": address.postal_code,
        "address_line_1": address.address_line_1,
        "address_line_2": address.address_line_2,
        "is_default": address.is_default,
    }


def _serialize_vendor_profile_brief(vendor: Vendor | None) -> dict | None:
    if vendor is None:
        return None
    return {
        "id": vendor.id,
        "business_name": vendor.business_name,
        "slug": vendor.slug,
        "phone_number": vendor.phone_number,
        "support_email": vendor.support_email,
        "status": vendor.status.value,
        "is_verified": vendor.is_verified,
    }


def _serialize_vendor_product_activity_item(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "stock_quantity": product.stock_quantity,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


def _serialize_vendor_order_activity_item(order: Order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value,
        "delivery_status": order.delivery_status,
        "total_amount": order.total_amount_value,
        "currency": order.currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _serialize_vendor_detail(vendor: Vendor) -> dict:
    products = sorted(
        vendor.products or [],
        key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id),
        reverse=True,
    )
    product_ids = [product.id for product in products]
    order_items = []
    if product_ids:
        order_items = (
            OrderItem.query.filter(OrderItem.product_id.in_(product_ids))
            .order_by(OrderItem.created_at.desc(), OrderItem.id.desc())
            .all()
        )

    order_map: dict[int, Order] = {}
    for item in order_items:
        if item.order is not None and item.order.id not in order_map:
            order_map[item.order.id] = item.order
    orders = sorted(
        order_map.values(),
        key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id),
        reverse=True,
    )

    reviews = []
    for product in products:
        reviews.extend(product.reviews or [])

    return {
        **_serialize_vendor_profile_brief(vendor),
        "description": vendor.description,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
        "user": _serialize_user_brief(vendor.user) if vendor.user is not None else None,
        "kyc_submission": (
            serialize_vendor_kyc_submission(vendor.kyc_submission)
            if vendor.kyc_submission is not None
            else None
        ),
        "metrics": {
            "products": len(products),
            "active_products": sum(1 for product in products if product.is_active),
            "low_stock_products": sum(
                1 for product in products if product.stock_quantity <= product.low_stock_threshold
            ),
            "orders": len(orders),
            "reviews": len(reviews),
        },
        "recent_products": [_serialize_vendor_product_activity_item(product) for product in products[:5]],
        "recent_orders": [_serialize_vendor_order_activity_item(order) for order in orders[:5]],
    }


def _serialize_delivery_agent_profile_brief(agent: DeliveryAgent | None) -> dict | None:
    if agent is None:
        return None
    return {
        "id": agent.id,
        "display_name": agent.display_name,
        "phone_number": agent.phone_number,
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


def _serialize_user_activity_item(*, item_id: int, label: str, status: str | None, created_at) -> dict:
    return {
        "id": item_id,
        "label": label,
        "status": status,
        "created_at": created_at.isoformat() if created_at else None,
    }


def _serialize_user_detail(user: User) -> dict:
    orders = sorted(user.orders or [], key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id), reverse=True)
    tickets = sorted(
        user.support_tickets or [],
        key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id),
        reverse=True,
    )
    reviews = sorted(
        user.reviews or [],
        key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id),
        reverse=True,
    )

    return {
        **_serialize_user_brief(user),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "must_change_password": user.must_change_password,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "addresses": [_serialize_address_brief(address) for address in user.addresses or []],
        "vendor_profile": _serialize_vendor_profile_brief(user.vendor_profile),
        "delivery_agent_profile": _serialize_delivery_agent_profile_brief(user.delivery_agent_profile),
        "metrics": {
            "orders": len(orders),
            "reviews": len(reviews),
            "support_tickets": len(tickets),
            "addresses": len(user.addresses or []),
            "wishlist_items": len(user.wishlist_items or []),
        },
        "recent_orders": [
            _serialize_user_activity_item(
                item_id=order.id,
                label=order.order_number,
                status=order.status.value,
                created_at=order.created_at,
            )
            for order in orders[:5]
        ],
        "recent_support_tickets": [
            _serialize_user_activity_item(
                item_id=ticket.id,
                label=ticket.subject,
                status=ticket.status.value,
                created_at=ticket.created_at,
            )
            for ticket in tickets[:5]
        ],
        "recent_reviews": [
            _serialize_user_activity_item(
                item_id=review.id,
                label=review.title or f"Review #{review.id}",
                status=str(getattr(review, "status", None)),
                created_at=review.created_at,
            )
            for review in reviews[:5]
        ],
    }


def _serialize_platform_setting(setting: PlatformSetting) -> dict:
    return {
        "id": setting.id,
        "key": setting.key,
        "value": setting.value,
        "description": setting.description,
        "is_public": setting.is_public,
        "updated_by_user_id": setting.updated_by_user_id,
        "updated_at": setting.updated_at.isoformat(),
    }


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
                    **_serialize_user_brief(user),
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                }
                for user in users
            ]
        }
    )


@admin_bp.post("/users")
@role_required(UserRole.ADMIN.value)
def create_user():
    payload = validate_admin_user_create_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if User.query.filter_by(email=payload["email"]).first():
        return validation_error({"email": "An account with that email already exists."})

    phone_number = payload["phone_number"]
    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return validation_error({"phone_number": "An account with that phone number already exists."})

    temporary_password = generate_temporary_password()
    user = User(
        email=payload["email"],
        password_hash=hash_password(temporary_password),
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        phone_number=phone_number,
        role=UserRole(payload["role"]),
        is_active=payload["is_active"],
        email_verified=payload["email_verified"],
        must_change_password=True,
    )
    db.session.add(user)
    db.session.flush()
    delivery = send_email(
        to_email=user.email,
        subject="Your TechHive account is ready",
        template="user_invitation",
        context={
            "user_name": user.full_name,
            "email": user.email,
            "temporary_password": temporary_password,
            "role": user.role.value.replace("_", " ").title(),
            "must_change_password": True,
        },
    )
    _add_audit_log(
        action="admin.user_created",
        entity_type="user",
        entity_id=user.id,
        metadata={"email": user.email, "role": user.role.value, "is_active": user.is_active, "delivery_status": delivery.get("status")},
    )
    db.session.commit()
    return jsonify({"item": _serialize_user_detail(user), "delivery": delivery}), 201


@admin_bp.get("/users/<int:user_id>")
@role_required(UserRole.ADMIN.value)
def get_user_detail(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        return _not_found("User not found.")
    return jsonify({"item": _serialize_user_detail(user)})


@admin_bp.get("/dashboard")
@role_required(UserRole.ADMIN.value)
def get_admin_dashboard():
    """
    Get the admin dashboard summary.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Admin dashboard summary.
    """
    return jsonify({"item": build_admin_dashboard()})


@admin_bp.get("/reports/overview")
@role_required(UserRole.ADMIN.value)
def get_admin_overview_report():
    return jsonify({"item": build_admin_overview_report()})


@admin_bp.get("/reports/vendors-performance")
@role_required(UserRole.ADMIN.value)
def get_admin_vendor_performance_report():
    limit = request.args.get("limit", default=10, type=int)
    if limit <= 0:
        return validation_error({"limit": "limit must be a positive integer."})
    return jsonify({"items": list_vendor_performance(limit=limit)})


@admin_bp.get("/campaigns")
@role_required(UserRole.ADMIN.value)
def get_admin_campaigns():
    days = request.args.get("days", default=30, type=int)
    if days <= 0:
        return validation_error({"days": "days must be a positive integer."})
    return jsonify(build_campaign_summary(days=days))


@admin_bp.get("/operations/queues")
@role_required(UserRole.ADMIN.value)
def get_admin_operations_queues():
    return jsonify({"item": build_admin_operations_queues()})


@admin_bp.get("/logs/mpesa")
@role_required(UserRole.ADMIN.value)
def get_mpesa_logs():
    limit = request.args.get("limit", default=100, type=int)
    if limit <= 0:
        return validation_error({"limit": "limit must be a positive integer."})
    return jsonify({"item": tail_mpesa_logs(limit=min(limit, 500))})


@admin_bp.post("/notifications/bulk")
@role_required(UserRole.ADMIN.value)
def send_bulk_notifications():
    """
    Send bulk notifications to users by role or explicit selection.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Bulk notification dispatch prepared.
    """
    payload = validate_bulk_notification_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    query = User.query.filter(User.is_active.is_(True))
    if payload["role"]:
        query = query.filter(User.role == UserRole(payload["role"]))
    if payload["user_ids"]:
        query = query.filter(User.id.in_(payload["user_ids"]))

    users = query.order_by(User.created_at.asc(), User.id.asc()).all()
    results = dispatch_bulk_notification(
        users=users,
        notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
        title=payload["title"],
        message=payload["message"],
        email_subject=payload["subject"],
        email_template="admin_announcement",
        email_context={"message": payload["message"], "title": payload["title"]},
        sms_message=payload["sms_message"],
        is_marketing=payload["is_marketing"],
        channels=set(payload["channels"]),
    )
    _add_audit_log(
        action="admin.notifications_bulk_sent",
        entity_type="notification",
        entity_id=0,
        metadata={
            "channels": payload["channels"],
            "role": payload["role"],
            "user_ids": payload["user_ids"],
            "targeted_count": results["targeted_count"],
            "is_marketing": payload["is_marketing"],
        },
    )
    db.session.commit()
    return jsonify(results)


@admin_bp.post("/emails/bulk")
@role_required(UserRole.ADMIN.value)
def send_bulk_email_campaign():
    """
    Send a bulk email campaign to users by role or explicit selection.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Bulk email campaign processed.
    """
    payload = validate_bulk_email_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    query = User.query.filter(User.is_active.is_(True))
    if payload["role"]:
        query = query.filter(User.role == UserRole(payload["role"]))
    if payload["user_ids"]:
        query = query.filter(User.id.in_(payload["user_ids"]))

    users = query.order_by(User.created_at.asc(), User.id.asc()).all()
    results = dispatch_bulk_email_campaign(
        users=users,
        subject=payload["subject"],
        headline=payload["headline"],
        message=payload["message"],
        preheader=payload["preheader"],
        is_marketing=payload["is_marketing"],
        cta_label=payload["cta_label"],
        cta_url=payload["cta_url"],
        dry_run=payload["dry_run"],
    )
    _add_audit_log(
        action="admin.bulk_email_sent",
        entity_type="notification",
        entity_id=0,
        metadata={
            "role": payload["role"],
            "user_ids": payload["user_ids"],
            "targeted_count": results["targeted_count"],
            "is_marketing": payload["is_marketing"],
            "dry_run": payload["dry_run"],
            "summary": results["summary"],
        },
    )
    db.session.commit()
    return jsonify(results)


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


@admin_bp.patch("/users/<int:user_id>/active")
@role_required(UserRole.ADMIN.value)
def update_user_active_state(user_id: int):
    """
    Activate or deactivate a user account.
    ---
    tags:
      - Admin
    responses:
      200:
        description: User activity state updated.
    """
    payload = validate_user_active_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    user, error = update_user_active(user_id=user_id, is_active=payload["is_active"])
    if error:
        return _not_found("User not found.")

    _add_audit_log(
        action="admin.user_active_updated",
        entity_type="user",
        entity_id=user.id,
        metadata={"is_active": user.is_active, "email": user.email},
    )
    db.session.commit()
    return jsonify({"item": {"id": user.id, "email": user.email, "is_active": user.is_active}})


@admin_bp.get("/settings")
@role_required(UserRole.ADMIN.value)
def list_platform_settings():
    settings = PlatformSetting.query.order_by(PlatformSetting.key.asc()).all()
    return jsonify({"items": [_serialize_platform_setting(setting) for setting in settings]})


@admin_bp.post("/settings")
@role_required(UserRole.ADMIN.value)
def create_platform_setting():
    payload = validate_platform_setting_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    existing = PlatformSetting.query.filter_by(key=payload["key"]).first()
    if existing is not None:
        return validation_error({"key": "A platform setting with that key already exists."})

    setting = PlatformSetting(
        key=payload["key"],
        value=payload["value"],
        description=payload["description"],
        is_public=payload["is_public"],
        updated_by_user_id=g.current_user.id,
    )
    db.session.add(setting)
    db.session.flush()
    _add_audit_log(
        action="admin.platform_setting_created",
        entity_type="platform_setting",
        entity_id=setting.id,
        metadata={"key": setting.key, "is_public": setting.is_public},
    )
    db.session.commit()
    return jsonify({"item": _serialize_platform_setting(setting)}), 201


@admin_bp.patch("/settings/<string:key>")
@role_required(UserRole.ADMIN.value)
def update_platform_setting(key: str):
    payload = validate_platform_setting_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    setting = PlatformSetting.query.filter_by(key=key).first()
    if setting is None:
        return _not_found("Platform setting not found.")

    for field in payload["provided_fields"]:
        setattr(setting, field, payload[field])
    setting.updated_by_user_id = g.current_user.id
    _add_audit_log(
        action="admin.platform_setting_updated",
        entity_type="platform_setting",
        entity_id=setting.id,
        metadata={"key": setting.key, "is_public": setting.is_public},
    )
    db.session.commit()
    return jsonify({"item": _serialize_platform_setting(setting)})


@admin_bp.get("/recommendations/settings")
@role_required(UserRole.ADMIN.value)
def list_recommendation_settings():
    return jsonify({"items": serialize_recommendation_settings()})


@admin_bp.patch("/recommendations/settings")
@role_required(UserRole.ADMIN.value)
def update_recommendation_settings():
    payload = validate_recommendation_settings_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    items = []
    for field, value in payload.items():
        db_key = RECOMMENDATION_SETTING_KEYS[field]["db_key"]
        setting = PlatformSetting.query.filter_by(key=db_key).first()
        if setting is None:
            setting = PlatformSetting(
                key=db_key,
                value=str(value),
                description=f"Recommendation setting for {field}.",
                is_public=False,
                updated_by_user_id=g.current_user.id,
            )
            db.session.add(setting)
            db.session.flush()
        else:
            setting.value = str(value)
            setting.updated_by_user_id = g.current_user.id
        items.append(setting)

    _add_audit_log(
        action="admin.recommendation_settings_updated",
        entity_type="platform_setting",
        entity_id=0,
        metadata={"fields": sorted(payload.keys())},
    )
    db.session.commit()
    return jsonify({"items": serialize_recommendation_settings()})


@admin_bp.get("/recommendations/metrics")
@role_required(UserRole.ADMIN.value)
def get_recommendation_metrics():
    days = request.args.get("days", default=30, type=int)
    if days <= 0:
        return validation_error({"days": "days must be a positive integer."})
    return jsonify({"item": summarize_recommendation_metrics(days=days)})


@admin_bp.get("/support-tickets")
@role_required(UserRole.ADMIN.value)
def list_support_tickets():
    status = str(request.args.get("status") or "").strip().lower() or None
    query = SupportTicket.query
    if status:
        allowed_statuses = {member.value for member in SupportTicketStatus}
        if status not in allowed_statuses:
            return validation_error({"status": "status must be a supported support ticket status."})
        query = query.filter(SupportTicket.status == SupportTicketStatus(status))

    tickets = query.order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc()).all()
    return jsonify({"items": [serialize_support_ticket(ticket) for ticket in tickets]})


@admin_bp.get("/notification-deliveries")
@role_required(UserRole.ADMIN.value)
def list_notification_deliveries():
    status = str(request.args.get("status") or "").strip().lower() or None
    channel = str(request.args.get("channel") or "").strip().lower() or None
    query = NotificationDelivery.query

    if status:
        allowed_statuses = {member.value for member in NotificationDeliveryStatus}
        if status not in allowed_statuses:
            return validation_error({"status": "status must be a supported notification delivery status."})
        query = query.filter(NotificationDelivery.status == NotificationDeliveryStatus(status))

    if channel:
        allowed_channels = {member.value for member in NotificationChannel}
        if channel not in allowed_channels:
            return validation_error({"channel": "channel must be in_app, email, or sms."})
        query = query.filter(NotificationDelivery.channel == NotificationChannel(channel))

    deliveries = query.order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc()).all()
    return jsonify(
        {
            "items": [serialize_notification_delivery(delivery) for delivery in deliveries],
            "summary": {"total": len(deliveries)},
        }
    )


@admin_bp.post("/notification-deliveries/retry")
@role_required(UserRole.ADMIN.value)
def retry_failed_notification_delivery():
    payload = validate_notification_delivery_retry_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    delivery = db.session.get(NotificationDelivery, payload["delivery_id"])
    if delivery is None:
        return _not_found("Notification delivery not found.")

    result, error = retry_notification_delivery(delivery)
    if error is not None:
        return validation_error({"delivery": error})

    _add_audit_log(
        action="admin.notification_delivery_retried",
        entity_type="notification_delivery",
        entity_id=delivery.id,
        metadata={"channel": delivery.channel.value, "status": delivery.status.value},
    )
    db.session.commit()
    return jsonify({"item": serialize_notification_delivery(delivery), "delivery": result})


@admin_bp.patch("/support-tickets/<int:ticket_id>/status")
@role_required(UserRole.ADMIN.value)
def update_support_ticket_status(ticket_id: int):
    payload = validate_support_ticket_status_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    ticket = db.session.get(SupportTicket, ticket_id)
    if ticket is None:
        return _not_found("Support ticket not found.")

    ticket.status = SupportTicketStatus(payload["status"])
    ticket.admin_note = payload["admin_note"]
    if ticket.status in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
        ticket.resolved_at = datetime.now(timezone.utc)
    else:
        ticket.resolved_at = None

    _add_audit_log(
        action="admin.support_ticket_updated",
        entity_type="support_ticket",
        entity_id=ticket.id,
        metadata={"status": ticket.status.value, "email": ticket.email},
    )
    notify_support_ticket_updated(ticket)
    db.session.commit()
    return jsonify({"item": serialize_support_ticket(ticket)})


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


@admin_bp.get("/vendors/<int:vendor_id>")
@role_required(UserRole.ADMIN.value)
def get_vendor_detail(vendor_id: int):
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return _not_found("Vendor not found.")

    return jsonify({"item": _serialize_vendor_detail(vendor)})


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
    payload = get_json_payload()
    limit, errors = parse_positive_int(
        payload.get("limit", current_app.config["MPESA_RECONCILIATION_BATCH_LIMIT"]),
        field_name="limit",
    )
    if errors:
        return validation_error(errors)

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
    payload = validate_named_entity_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    uniqueness_error = ensure_unique_category_slug(payload["slug"])
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

    parent_id = payload.get("parent_id")
    if parent_id is not None:
        parent = db.session.get(Category, parent_id)
        if parent is None:
            return validation_error({"parent_id": "Parent category not found."})

    category = Category(
        parent_id=parent_id,
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
        metadata={"name": category.name, "slug": category.slug, "parent_id": category.parent_id},
    )
    db.session.commit()
    return jsonify({"item": serialize_category(category)}), 201


@admin_bp.patch("/categories/<int:category_id>")
@role_required(UserRole.ADMIN.value)
def update_category_detail(category_id: int):
    payload = validate_named_entity_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    category, error = update_category(category_id=category_id, payload=payload)
    if error:
        if error.status_code == 404:
            return _not_found("Category not found.")
        return validation_error(error.details)

    _add_audit_log(
        action="admin.category_updated",
        entity_type="category",
        entity_id=category.id,
        metadata={"name": category.name, "slug": category.slug, "is_active": category.is_active, "parent_id": category.parent_id},
    )
    db.session.commit()
    return jsonify({"item": serialize_category(category)})


@admin_bp.delete("/categories/<int:category_id>")
@role_required(UserRole.ADMIN.value)
def remove_category(category_id: int):
    category, error = delete_category(category_id=category_id)
    if error:
        if error.status_code == 404:
            return _not_found("Category not found.")
        return validation_error(error.details)

    _add_audit_log(
        action="admin.category_deleted",
        entity_type="category",
        entity_id=category.id,
        metadata={"name": category.name, "slug": category.slug, "parent_id": category.parent_id},
    )
    db.session.commit()
    return jsonify({"message": "Category deleted successfully."})


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
    payload = validate_named_entity_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    uniqueness_error = ensure_unique_brand_slug(payload["slug"])
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

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


@admin_bp.get("/categories")
@role_required(UserRole.ADMIN.value)
def list_categories():
    categories = Category.query.order_by(Category.name.asc(), Category.id.asc()).all()
    return jsonify({"items": [serialize_category(category) for category in categories]})


@admin_bp.get("/brands")
@role_required(UserRole.ADMIN.value)
def list_brands():
    brands = Brand.query.order_by(Brand.name.asc(), Brand.id.asc()).all()
    return jsonify({"items": [serialize_brand(brand) for brand in brands]})


@admin_bp.get("/product-types")
@role_required(UserRole.ADMIN.value)
def list_product_types():
    product_types = ProductType.query.order_by(ProductType.name.asc(), ProductType.id.asc()).all()
    return jsonify({"items": [_serialize_product_type(product_type) for product_type in product_types]})


@admin_bp.post("/product-types")
@role_required(UserRole.ADMIN.value)
def create_product_type():
    payload = validate_product_type_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    duplicate = ProductType.query.filter_by(slug=payload["slug"]).first()
    if duplicate is not None:
        return validation_error({"slug": "A product type with that slug already exists."})

    duplicate_name = ProductType.query.filter_by(name=payload["name"]).first()
    if duplicate_name is not None:
        return validation_error({"name": "A product type with that name already exists."})

    product_type = ProductType(
        name=payload["name"],
        slug=payload["slug"],
        requires_shipping=payload["requires_shipping"],
        track_stock=payload["track_stock"],
        is_active=payload["is_active"],
    )
    db.session.add(product_type)
    db.session.flush()
    _add_audit_log(
        action="admin.product_type_created",
        entity_type="product_type",
        entity_id=product_type.id,
        metadata={"slug": product_type.slug},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_type(product_type)}), 201


@admin_bp.patch("/product-types/<int:product_type_id>")
@role_required(UserRole.ADMIN.value)
def update_product_type_detail(product_type_id: int):
    payload = validate_product_type_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product_type = db.session.get(ProductType, product_type_id)
    if product_type is None:
        return _not_found("Product type not found.")

    if "slug" in payload["provided_fields"]:
        duplicate = ProductType.query.filter(ProductType.slug == payload["slug"], ProductType.id != product_type.id).first()
        if duplicate is not None:
            return validation_error({"slug": "A product type with that slug already exists."})

    if "name" in payload["provided_fields"]:
        duplicate_name = ProductType.query.filter(ProductType.name == payload["name"], ProductType.id != product_type.id).first()
        if duplicate_name is not None:
            return validation_error({"name": "A product type with that name already exists."})

    for field in ("name", "slug", "requires_shipping", "track_stock", "is_active"):
        if field in payload["provided_fields"]:
            setattr(product_type, field, payload[field])

    _add_audit_log(
        action="admin.product_type_updated",
        entity_type="product_type",
        entity_id=product_type.id,
        metadata={"slug": product_type.slug},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_type(product_type)})


@admin_bp.delete("/product-types/<int:product_type_id>")
@role_required(UserRole.ADMIN.value)
def delete_product_type_detail(product_type_id: int):
    product_type = db.session.get(ProductType, product_type_id)
    if product_type is None:
        return _not_found("Product type not found.")

    _add_audit_log(
        action="admin.product_type_deleted",
        entity_type="product_type",
        entity_id=product_type.id,
        metadata={"slug": product_type.slug},
    )
    db.session.delete(product_type)
    db.session.commit()
    return jsonify({"message": "Product type deleted successfully."})


@admin_bp.get("/attributes")
@role_required(UserRole.ADMIN.value)
def list_product_attributes():
    attributes = ProductAttribute.query.order_by(ProductAttribute.name.asc(), ProductAttribute.id.asc()).all()
    return jsonify({"items": [_serialize_product_attribute(attribute) for attribute in attributes]})


@admin_bp.post("/attributes")
@role_required(UserRole.ADMIN.value)
def create_product_attribute():
    payload = validate_product_attribute_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product_type = db.session.get(ProductType, payload["product_type_id"])
    if product_type is None:
        return validation_error({"product_type_id": "Selected product type was not found."})

    duplicate = ProductAttribute.query.filter_by(
        product_type_id=product_type.id,
        code=payload["code"],
    ).first()
    if duplicate is not None:
        return validation_error({"code": "An attribute with that code already exists for this product type."})

    attribute = ProductAttribute(
        product_type_id=product_type.id,
        name=payload["name"],
        code=payload["code"],
        type=payload["type"],
        required=payload["required"],
        option_group_id=payload["option_group_id"],
    )
    db.session.add(attribute)
    db.session.flush()
    _add_audit_log(
        action="admin.product_attribute_created",
        entity_type="product_attribute",
        entity_id=attribute.id,
        metadata={"code": attribute.code, "product_type_id": attribute.product_type_id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_attribute(attribute)}), 201


@admin_bp.patch("/attributes/<int:attribute_id>")
@role_required(UserRole.ADMIN.value)
def update_product_attribute_detail(attribute_id: int):
    payload = validate_product_attribute_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    attribute = db.session.get(ProductAttribute, attribute_id)
    if attribute is None:
        return _not_found("Product attribute not found.")

    if "code" in payload["provided_fields"]:
        duplicate = ProductAttribute.query.filter(
            ProductAttribute.product_type_id == attribute.product_type_id,
            ProductAttribute.code == payload["code"],
            ProductAttribute.id != attribute.id,
        ).first()
        if duplicate is not None:
            return validation_error({"code": "An attribute with that code already exists for this product type."})

    for field in ("name", "code", "type", "required", "option_group_id"):
        if field in payload["provided_fields"]:
            setattr(attribute, field, payload[field])

    _add_audit_log(
        action="admin.product_attribute_updated",
        entity_type="product_attribute",
        entity_id=attribute.id,
        metadata={"code": attribute.code, "product_type_id": attribute.product_type_id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_attribute(attribute)})


@admin_bp.delete("/attributes/<int:attribute_id>")
@role_required(UserRole.ADMIN.value)
def delete_product_attribute_detail(attribute_id: int):
    attribute = db.session.get(ProductAttribute, attribute_id)
    if attribute is None:
        return _not_found("Product attribute not found.")

    _add_audit_log(
        action="admin.product_attribute_deleted",
        entity_type="product_attribute",
        entity_id=attribute.id,
        metadata={"code": attribute.code, "product_type_id": attribute.product_type_id},
    )
    db.session.delete(attribute)
    db.session.commit()
    return jsonify({"message": "Product attribute deleted successfully."})


@admin_bp.get("/options")
@role_required(UserRole.ADMIN.value)
def list_product_options():
    options = ProductOption.query.order_by(ProductOption.sort_order.asc(), ProductOption.name.asc(), ProductOption.id.asc()).all()
    return jsonify({"items": [_serialize_product_option(option) for option in options]})


@admin_bp.post("/options")
@role_required(UserRole.ADMIN.value)
def create_product_option():
    payload = validate_product_option_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    duplicate = ProductOption.query.filter_by(code=payload["code"]).first()
    if duplicate is not None:
        return validation_error({"code": "A product option with that code already exists."})

    option = ProductOption(
        name=payload["name"],
        code=payload["code"],
        type=payload["type"],
        required=payload["required"],
        help_text=payload["help_text"],
        sort_order=payload["sort_order"],
    )
    db.session.add(option)
    db.session.flush()
    _add_audit_log(
        action="admin.product_option_created",
        entity_type="product_option",
        entity_id=option.id,
        metadata={"code": option.code},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_option(option)}), 201


@admin_bp.patch("/options/<int:option_id>")
@role_required(UserRole.ADMIN.value)
def update_product_option_detail(option_id: int):
    payload = validate_product_option_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    option = db.session.get(ProductOption, option_id)
    if option is None:
        return _not_found("Product option not found.")

    if "code" in payload["provided_fields"]:
        duplicate = ProductOption.query.filter(
            ProductOption.code == payload["code"],
            ProductOption.id != option.id,
        ).first()
        if duplicate is not None:
            return validation_error({"code": "A product option with that code already exists."})

    for field in ("name", "code", "type", "required", "help_text", "sort_order"):
        if field in payload:
            setattr(option, field, payload[field])

    _add_audit_log(
        action="admin.product_option_updated",
        entity_type="product_option",
        entity_id=option.id,
        metadata={"code": option.code},
    )
    db.session.commit()
    return jsonify({"item": _serialize_product_option(option)})


@admin_bp.delete("/options/<int:option_id>")
@role_required(UserRole.ADMIN.value)
def delete_product_option_detail(option_id: int):
    option = db.session.get(ProductOption, option_id)
    if option is None:
        return _not_found("Product option not found.")

    _add_audit_log(
        action="admin.product_option_deleted",
        entity_type="product_option",
        entity_id=option.id,
        metadata={"code": option.code},
    )
    db.session.delete(option)
    db.session.commit()
    return jsonify({"message": "Product option deleted successfully."})


@admin_bp.get("/offers/meta")
@role_required(UserRole.ADMIN.value)
def get_offer_meta():
    return jsonify(
        {
            "offer_types": [
                {"value": "site", "label": "Site offer"},
                {"value": "voucher", "label": "Voucher offer"},
                {"value": "shipping", "label": "Shipping offer"},
            ],
            "offer_statuses": [
                {"value": "Open", "label": "Open"},
                {"value": "Suspended", "label": "Suspended"},
                {"value": "Consumed", "label": "Consumed"},
            ],
            "condition_types": [
                {"value": "count", "label": "Count"},
                {"value": "value", "label": "Basket value"},
                {"value": "coverage", "label": "Coverage"},
            ],
            "benefit_types": [
                {"value": "percentage", "label": "Percentage discount"},
                {"value": "fixed", "label": "Fixed discount"},
                {"value": "multibuy", "label": "Multibuy"},
                {"value": "shipping", "label": "Shipping benefit"},
            ],
        }
    )


@admin_bp.get("/offers")
@role_required(UserRole.ADMIN.value)
def list_offers():
    offers = Offer.query.order_by(Offer.priority.desc(), Offer.created_at.desc(), Offer.id.desc()).all()
    return jsonify({"items": [_serialize_offer(offer) for offer in offers]})


@admin_bp.post("/offers")
@role_required(UserRole.ADMIN.value)
def create_offer():
    payload = validate_offer_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    condition = db.session.get(OfferCondition, payload["condition_id"])
    if condition is None:
        return validation_error({"condition_id": "Selected condition was not found."})

    benefit = db.session.get(OfferBenefit, payload["benefit_id"])
    if benefit is None:
        return validation_error({"benefit_id": "Selected benefit was not found."})

    existing = Offer.query.filter(Offer.slug == payload["slug"]).first()
    if existing is not None:
        return validation_error({"slug": "slug must be unique."})

    offer = Offer(**payload)
    db.session.add(offer)
    db.session.flush()
    _add_audit_log(
        action="admin.offer_created",
        entity_type="offer",
        entity_id=offer.id,
        metadata={"slug": offer.slug, "status": offer.status, "offer_type": offer.offer_type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer(offer)}), 201


@admin_bp.patch("/offers/<int:offer_id>")
@role_required(UserRole.ADMIN.value)
def update_offer_detail(offer_id: int):
    payload = validate_offer_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    offer = db.session.get(Offer, offer_id)
    if offer is None:
        return _not_found("Offer not found.")

    if "condition_id" in payload["provided_fields"]:
        condition = db.session.get(OfferCondition, payload["condition_id"])
        if condition is None:
            return validation_error({"condition_id": "Selected condition was not found."})

    if "benefit_id" in payload["provided_fields"]:
        benefit = db.session.get(OfferBenefit, payload["benefit_id"])
        if benefit is None:
            return validation_error({"benefit_id": "Selected benefit was not found."})

    if "slug" in payload["provided_fields"]:
        existing = Offer.query.filter(Offer.slug == payload["slug"], Offer.id != offer.id).first()
        if existing is not None:
            return validation_error({"slug": "slug must be unique."})

    for field in (
        "name",
        "slug",
        "description",
        "offer_type",
        "exclusive",
        "status",
        "priority",
        "start_datetime",
        "end_datetime",
        "condition_id",
        "benefit_id",
    ):
        if field in payload["provided_fields"]:
            setattr(offer, field, payload[field])

    _add_audit_log(
        action="admin.offer_updated",
        entity_type="offer",
        entity_id=offer.id,
        metadata={"slug": offer.slug, "status": offer.status, "offer_type": offer.offer_type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer(offer)})


@admin_bp.patch("/offers/<int:offer_id>/status")
@role_required(UserRole.ADMIN.value)
def update_offer_status(offer_id: int):
    payload = validate_offer_status_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    offer = db.session.get(Offer, offer_id)
    if offer is None:
        return _not_found("Offer not found.")

    offer.status = payload["status"]
    _add_audit_log(
        action="admin.offer_status_updated",
        entity_type="offer",
        entity_id=offer.id,
        metadata={"slug": offer.slug, "status": offer.status},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer(offer)})


@admin_bp.delete("/offers/<int:offer_id>")
@role_required(UserRole.ADMIN.value)
def delete_offer_detail(offer_id: int):
    offer = db.session.get(Offer, offer_id)
    if offer is None:
        return _not_found("Offer not found.")

    _add_audit_log(
        action="admin.offer_deleted",
        entity_type="offer",
        entity_id=offer.id,
        metadata={"slug": offer.slug, "status": offer.status},
    )
    db.session.delete(offer)
    db.session.commit()
    return jsonify({"message": "Offer deleted successfully."})


@admin_bp.get("/offers/conditions")
@role_required(UserRole.ADMIN.value)
def list_offer_conditions():
    items = OfferCondition.query.order_by(OfferCondition.created_at.desc(), OfferCondition.id.desc()).all()
    return jsonify({"items": [_serialize_offer_condition(item) for item in items]})


@admin_bp.post("/offers/conditions")
@role_required(UserRole.ADMIN.value)
def create_offer_condition():
    payload = validate_offer_component_payload(get_json_payload(), kind="condition")
    if "errors" in payload:
        return validation_error(payload["errors"])

    condition = OfferCondition(**payload)
    db.session.add(condition)
    db.session.flush()
    _add_audit_log(
        action="admin.offer_condition_created",
        entity_type="offer_condition",
        entity_id=condition.id,
        metadata={"type": condition.type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer_condition(condition)}), 201


@admin_bp.patch("/offers/conditions/<int:condition_id>")
@role_required(UserRole.ADMIN.value)
def update_offer_condition_detail(condition_id: int):
    payload = validate_offer_component_update_payload(get_json_payload(), kind="condition")
    if "errors" in payload:
        return validation_error(payload["errors"])

    condition = db.session.get(OfferCondition, condition_id)
    if condition is None:
        return _not_found("Offer condition not found.")

    for field in ("type", "range_id", "value", "proxy_class"):
        if field in payload["provided_fields"]:
            setattr(condition, field, payload[field])

    _add_audit_log(
        action="admin.offer_condition_updated",
        entity_type="offer_condition",
        entity_id=condition.id,
        metadata={"type": condition.type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer_condition(condition)})


@admin_bp.delete("/offers/conditions/<int:condition_id>")
@role_required(UserRole.ADMIN.value)
def delete_offer_condition_detail(condition_id: int):
    condition = db.session.get(OfferCondition, condition_id)
    if condition is None:
        return _not_found("Offer condition not found.")

    linked_offer = Offer.query.filter_by(condition_id=condition.id).first()
    if linked_offer is not None:
        return validation_error({"condition": "Delete or update linked offers before deleting this condition."})

    _add_audit_log(
        action="admin.offer_condition_deleted",
        entity_type="offer_condition",
        entity_id=condition.id,
        metadata={"type": condition.type},
    )
    db.session.delete(condition)
    db.session.commit()
    return jsonify({"message": "Offer condition deleted successfully."})


@admin_bp.get("/offers/benefits")
@role_required(UserRole.ADMIN.value)
def list_offer_benefits():
    items = OfferBenefit.query.order_by(OfferBenefit.created_at.desc(), OfferBenefit.id.desc()).all()
    return jsonify({"items": [_serialize_offer_benefit(item) for item in items]})


@admin_bp.post("/offers/benefits")
@role_required(UserRole.ADMIN.value)
def create_offer_benefit():
    payload = validate_offer_component_payload(get_json_payload(), kind="benefit")
    if "errors" in payload:
        return validation_error(payload["errors"])

    benefit = OfferBenefit(**payload)
    db.session.add(benefit)
    db.session.flush()
    _add_audit_log(
        action="admin.offer_benefit_created",
        entity_type="offer_benefit",
        entity_id=benefit.id,
        metadata={"type": benefit.type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer_benefit(benefit)}), 201


@admin_bp.patch("/offers/benefits/<int:benefit_id>")
@role_required(UserRole.ADMIN.value)
def update_offer_benefit_detail(benefit_id: int):
    payload = validate_offer_component_update_payload(get_json_payload(), kind="benefit")
    if "errors" in payload:
        return validation_error(payload["errors"])

    benefit = db.session.get(OfferBenefit, benefit_id)
    if benefit is None:
        return _not_found("Offer benefit not found.")

    for field in ("type", "range_id", "value", "proxy_class", "max_affected_items"):
        if field in payload["provided_fields"]:
            setattr(benefit, field, payload[field])

    _add_audit_log(
        action="admin.offer_benefit_updated",
        entity_type="offer_benefit",
        entity_id=benefit.id,
        metadata={"type": benefit.type},
    )
    db.session.commit()
    return jsonify({"item": _serialize_offer_benefit(benefit)})


@admin_bp.delete("/offers/benefits/<int:benefit_id>")
@role_required(UserRole.ADMIN.value)
def delete_offer_benefit_detail(benefit_id: int):
    benefit = db.session.get(OfferBenefit, benefit_id)
    if benefit is None:
        return _not_found("Offer benefit not found.")

    linked_offer = Offer.query.filter_by(benefit_id=benefit.id).first()
    if linked_offer is not None:
        return validation_error({"benefit": "Delete or update linked offers before deleting this benefit."})

    _add_audit_log(
        action="admin.offer_benefit_deleted",
        entity_type="offer_benefit",
        entity_id=benefit.id,
        metadata={"type": benefit.type},
    )
    db.session.delete(benefit)
    db.session.commit()
    return jsonify({"message": "Offer benefit deleted successfully."})


@admin_bp.get("/stock-alerts")
@role_required(UserRole.ADMIN.value)
def list_stock_alerts():
    _ensure_stock_alerts_for_low_stock_products()
    alerts = ProductStockAlert.query.order_by(ProductStockAlert.created_at.desc(), ProductStockAlert.id.desc()).all()
    return jsonify({"items": [_serialize_stock_alert(alert) for alert in alerts]})


@admin_bp.patch("/stock-alerts/<int:alert_id>")
@role_required(UserRole.ADMIN.value)
def update_stock_alert_detail(alert_id: int):
    payload = validate_stock_alert_status_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    alert = db.session.get(ProductStockAlert, alert_id)
    if alert is None:
        return _not_found("Stock alert not found.")

    alert.status = payload["status"]
    alert.closed_at = datetime.now(timezone.utc) if payload["status"] == "closed" else None
    _add_audit_log(
        action="admin.stock_alert_updated",
        entity_type="stock_alert",
        entity_id=alert.id,
        metadata={"status": alert.status, "product_id": alert.product_id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_stock_alert(alert)})


@admin_bp.get("/reviews")
@role_required(UserRole.ADMIN.value)
def list_reviews():
    reviews = Review.query.order_by(Review.created_at.desc(), Review.id.desc()).all()
    return jsonify({"items": [_serialize_admin_review(review) for review in reviews]})


@admin_bp.patch("/reviews/<int:review_id>")
@role_required(UserRole.ADMIN.value)
def update_review_detail(review_id: int):
    payload = validate_admin_review_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    review = db.session.get(Review, review_id)
    if review is None:
        return _not_found("Review not found.")

    if "status" in payload["provided_fields"]:
        review.status = payload["status"]
    if "title" in payload["provided_fields"]:
        review.title = payload["title"]
    if "body" in payload["provided_fields"]:
        review.comment = payload["body"]
    if "score" in payload["provided_fields"]:
        review.rating = payload["score"]

    _add_audit_log(
        action="admin.review_updated",
        entity_type="review",
        entity_id=review.id,
        metadata={"product_id": review.product_id, "status": review.status},
    )
    db.session.commit()
    return jsonify({"item": _serialize_admin_review(review)})


@admin_bp.delete("/reviews/<int:review_id>")
@role_required(UserRole.ADMIN.value)
def delete_review_detail(review_id: int):
    review = db.session.get(Review, review_id)
    if review is None:
        return _not_found("Review not found.")

    _add_audit_log(
        action="admin.review_deleted",
        entity_type="review",
        entity_id=review.id,
        metadata={"product_id": review.product_id, "status": review.status},
    )
    db.session.delete(review)
    db.session.commit()
    return jsonify({"message": "Review deleted successfully."})


@admin_bp.patch("/brands/<int:brand_id>")
@role_required(UserRole.ADMIN.value)
def update_brand_detail(brand_id: int):
    payload = validate_named_entity_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    brand, error = update_brand(brand_id=brand_id, payload=payload)
    if error:
        if error.status_code == 404:
            return _not_found("Brand not found.")
        return validation_error(error.details)

    _add_audit_log(
        action="admin.brand_updated",
        entity_type="brand",
        entity_id=brand.id,
        metadata={"name": brand.name, "slug": brand.slug, "is_active": brand.is_active},
    )
    db.session.commit()
    return jsonify({"item": serialize_brand(brand)})


@admin_bp.delete("/brands/<int:brand_id>")
@role_required(UserRole.ADMIN.value)
def remove_brand(brand_id: int):
    brand, error = delete_brand(brand_id=brand_id)
    if error:
        if error.status_code == 404:
            return _not_found("Brand not found.")
        return validation_error(error.details)

    _add_audit_log(
        action="admin.brand_deleted",
        entity_type="brand",
        entity_id=brand.id,
        metadata={"name": brand.name, "slug": brand.slug},
    )
    db.session.commit()
    return jsonify({"message": "Brand deleted successfully."})


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


@admin_bp.post("/products")
@role_required(UserRole.ADMIN.value)
def create_product():
    payload = validate_admin_product_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    vendor = db.session.get(Vendor, payload["vendor_id"])
    if vendor is None:
        return validation_error({"vendor_id": "Selected vendor was not found."})

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
        compare_at_price=payload["compare_at_price"],
        currency=payload["currency"],
        stock_quantity=payload["stock_quantity"],
        low_stock_threshold=payload["low_stock_threshold"],
        weight_grams=payload["weight_grams"],
        dimensions_text=payload["dimensions_text"],
        is_active=payload["is_active"],
        is_featured=payload["is_featured"],
    )
    db.session.add(product)
    db.session.flush()
    _add_audit_log(
        action="admin.product_created",
        entity_type="product",
        entity_id=product.id,
        metadata={"slug": product.slug, "vendor_id": product.vendor_id, "stock_quantity": product.stock_quantity, "low_stock_threshold": product.low_stock_threshold},
    )
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)}), 201


@admin_bp.get("/products/<int:product_id>")
@role_required(UserRole.ADMIN.value)
def get_product_detail(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")
    return jsonify({"item": serialize_product(product, include_related=True)})


@admin_bp.patch("/products/<int:product_id>")
@role_required(UserRole.ADMIN.value)
def update_product_detail(product_id: int):
    payload = validate_admin_product_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    if "vendor_id" in payload["provided_fields"]:
        vendor = db.session.get(Vendor, payload["vendor_id"])
        if vendor is None:
            return validation_error({"vendor_id": "Selected vendor was not found."})
        product.vendor_id = vendor.id

    if "category_id" in payload["provided_fields"]:
        category, category_error = get_active_category(payload["category_id"])
        if category_error:
            return validation_error(category_error.details)
        product.category_id = category.id

    if "brand_id" in payload["provided_fields"]:
        brand, brand_error = get_active_brand(payload["brand_id"])
        if brand_error:
            return validation_error(brand_error.details)
        product.brand_id = brand.id

    uniqueness_error = ensure_unique_product_slug_and_sku_for_update(
        slug=payload.get("slug"),
        sku=payload.get("sku"),
        product_id=product.id,
    )
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

    for field in (
        "name",
        "slug",
        "sku",
        "price",
        "compare_at_price",
        "currency",
        "stock_quantity",
        "low_stock_threshold",
        "weight_grams",
        "dimensions_text",
        "short_description",
        "description",
        "is_active",
        "is_featured",
    ):
        if field in payload["provided_fields"]:
            setattr(product, field, payload[field])

    _add_audit_log(
        action="admin.product_updated",
        entity_type="product",
        entity_id=product.id,
        metadata={"slug": product.slug, "vendor_id": product.vendor_id, "stock_quantity": product.stock_quantity, "low_stock_threshold": product.low_stock_threshold},
    )
    db.session.commit()
    return jsonify({"item": serialize_product(product, include_related=True)})


@admin_bp.delete("/products/<int:product_id>")
@role_required(UserRole.ADMIN.value)
def delete_product_detail(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    _add_audit_log(
        action="admin.product_deleted",
        entity_type="product",
        entity_id=product.id,
        metadata={"slug": product.slug, "vendor_id": product.vendor_id},
    )
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully."})


@admin_bp.post("/products/<int:product_id>/images")
@role_required(UserRole.ADMIN.value)
def upload_product_image(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    upload = request.files.get("file") or request.files.get("image")
    stored, storage_error = save_uploaded_file(
        upload=upload,
        folder=f"products/{product.id}",
        allowed_extensions=IMAGE_EXTENSIONS,
    )
    if storage_error is not None:
        return validation_error({storage_error.field: storage_error.message})

    sort_order_raw = request.form.get("sort_order", "0")
    try:
        sort_order = int(sort_order_raw)
    except (TypeError, ValueError):
        return validation_error({"sort_order": "sort_order must be an integer."})

    is_primary = str(request.form.get("is_primary", "false")).lower() == "true"
    if not product.images:
        is_primary = True
    if is_primary:
        for image in product.images:
            image.is_primary = False

    image = ProductImage(
        product_id=product.id,
        image_url=stored["url"],
        alt_text=str(request.form.get("alt_text") or request.form.get("alt") or "").strip() or None,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    db.session.add(image)
    db.session.flush()
    _add_audit_log(
        action="admin.product_image_uploaded",
        entity_type="product",
        entity_id=product.id,
        metadata={"image_id": image.id, "is_primary": image.is_primary},
    )
    db.session.commit()
    return jsonify({"item": serialize_product_image(image)}), 201


@admin_bp.delete("/products/<int:product_id>/images/<int:image_id>")
@role_required(UserRole.ADMIN.value)
def delete_product_image_detail(product_id: int, image_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    image = ProductImage.query.filter_by(id=image_id, product_id=product.id).first()
    if image is None:
        return _not_found("Product image not found.")

    if image.image_url.startswith("/media/"):
        delete_stored_file(image.image_url.removeprefix("/media/"))

    was_primary = image.is_primary
    db.session.delete(image)
    db.session.flush()

    if was_primary:
        replacement = (
            ProductImage.query.filter_by(product_id=product.id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            .first()
        )
        if replacement is not None:
            replacement.is_primary = True

    _add_audit_log(
        action="admin.product_image_deleted",
        entity_type="product",
        entity_id=product.id,
        metadata={"image_id": image_id},
    )
    db.session.commit()
    return jsonify({"message": "Product image deleted successfully."})


@admin_bp.get("/media")
@role_required(UserRole.ADMIN.value)
def list_media_assets():
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 24)
    query_text = str(request.args.get("q", "") or "").strip()
    product_id_raw = request.args.get("product_id")

    page_number, page_errors = parse_positive_int(page, field_name="page")
    if page_errors:
        return validation_error(page_errors)

    page_size_value, page_size_errors = parse_positive_int(page_size, field_name="page_size")
    if page_size_errors:
        return validation_error(page_size_errors)

    query = ProductImage.query.join(Product)
    if product_id_raw not in (None, ""):
        product_id, product_errors = parse_positive_int(product_id_raw, field_name="product_id")
        if product_errors:
            return validation_error(product_errors)
        query = query.filter(ProductImage.product_id == product_id)

    if query_text:
        like = f"%{query_text}%"
        query = query.filter(
            or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                ProductImage.alt_text.ilike(like),
                ProductImage.image_url.ilike(like),
            )
        )

    total_assets = ProductImage.query.count()
    matching_assets = query.count()
    items = (
        query.order_by(ProductImage.created_at.desc(), ProductImage.id.desc())
        .offset((page_number - 1) * page_size_value)
        .limit(page_size_value)
        .all()
    )
    total_pages = max(1, (matching_assets + page_size_value - 1) // page_size_value)

    return jsonify(
        {
            "items": [_serialize_media_asset(image) for image in items],
            "pagination": {
                "page": page_number,
                "page_size": page_size_value,
                "total": matching_assets,
                "num_pages": total_pages,
            },
            "summary": {
                "total": total_assets,
                "matching": matching_assets,
            },
        }
    )


@admin_bp.post("/media")
@role_required(UserRole.ADMIN.value)
def upload_media_asset():
    product_id_raw = request.form.get("product_id")
    product_id, product_errors = parse_positive_int(product_id_raw, field_name="product_id")
    if product_errors:
        return validation_error(product_errors)

    product = db.session.get(Product, product_id)
    if product is None:
        return _not_found("Product not found.")

    upload = request.files.get("file") or request.files.get("image")
    stored, storage_error = save_uploaded_file(
        upload=upload,
        folder=f"products/{product.id}",
        allowed_extensions=IMAGE_EXTENSIONS,
    )
    if storage_error is not None:
        return validation_error({storage_error.field: storage_error.message})

    next_sort_order = 0
    if product.images:
        next_sort_order = max(image.sort_order for image in product.images) + 1

    is_primary = not bool(product.images)
    image = ProductImage(
        product_id=product.id,
        image_url=stored["url"],
        alt_text=str(request.form.get("alt_text") or request.form.get("alt") or "").strip() or None,
        is_primary=is_primary,
        sort_order=next_sort_order,
    )
    db.session.add(image)
    db.session.flush()
    _add_audit_log(
        action="admin.media_uploaded",
        entity_type="product",
        entity_id=product.id,
        metadata={"image_id": image.id, "is_primary": image.is_primary},
    )
    db.session.commit()
    return jsonify({"item": _serialize_media_asset(image)}), 201


@admin_bp.delete("/media/<int:image_id>")
@role_required(UserRole.ADMIN.value)
def delete_media_asset(image_id: int):
    image = db.session.get(ProductImage, image_id)
    if image is None:
        return _not_found("Media asset not found.")

    product_id = image.product_id
    was_primary = image.is_primary
    if image.image_url.startswith("/media/"):
        delete_stored_file(image.image_url.removeprefix("/media/"))

    db.session.delete(image)
    db.session.flush()

    if was_primary:
        replacement = (
            ProductImage.query.filter_by(product_id=product_id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            .first()
        )
        if replacement is not None:
            replacement.is_primary = True

    _add_audit_log(
        action="admin.media_deleted",
        entity_type="product",
        entity_id=product_id,
        metadata={"image_id": image_id},
    )
    db.session.commit()
    return jsonify({"message": "Media asset deleted successfully."})


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
    payload = validate_product_active_payload(get_json_payload())
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


@admin_bp.get("/orders/<int:order_id>")
@role_required(UserRole.ADMIN.value)
def get_order_detail(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        return _not_found("Order not found.")
    return jsonify({"item": serialize_order(order, include_items=True)})


@admin_bp.patch("/orders/<int:order_id>")
@role_required(UserRole.ADMIN.value)
def update_order_detail(order_id: int):
    payload = validate_admin_order_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    order = db.session.get(Order, order_id)
    if order is None:
        return _not_found("Order not found.")

    if "status" in payload["provided_fields"]:
        transition_error = transition_order(order, OrderStatus(payload["status"]))
        if transition_error is not None:
            return jsonify({"error": {"code": transition_error.code, "message": transition_error.message}}), 400

    if "delivery_agent_id" in payload["provided_fields"]:
        delivery_agent_id = payload["delivery_agent_id"]
        if delivery_agent_id is None:
            order.delivery_agent_id = None
        else:
            agent = db.session.get(DeliveryAgent, delivery_agent_id)
            if agent is None or not agent.is_active:
                return validation_error({"delivery_agent_id": "Selected delivery agent was not found."})
            order.delivery_agent_id = agent.id

    for field in ("delivery_status", "tracking_token", "notes"):
        if field in payload["provided_fields"]:
            setattr(order, field, payload[field])

    _add_audit_log(
        action="admin.order_updated",
        entity_type="order",
        entity_id=order.id,
        metadata={
            "order_number": order.order_number,
            "status": order.status.value,
            "delivery_status": order.delivery_status,
            "delivery_agent_id": order.delivery_agent_id,
        },
    )
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})


@admin_bp.get("/delivery-agents")
@role_required(UserRole.ADMIN.value)
def list_delivery_agents():
    agents = DeliveryAgent.query.order_by(DeliveryAgent.display_name.asc(), DeliveryAgent.id.asc()).all()
    return jsonify({"items": [_serialize_delivery_agent_brief(agent) for agent in agents]})


@admin_bp.get("/shipping/zones")
@role_required(UserRole.ADMIN.value)
def list_shipping_zones():
    zones = DeliveryZone.query.order_by(DeliveryZone.city.asc(), DeliveryZone.id.asc()).all()
    return jsonify({"items": [_serialize_delivery_zone(zone) for zone in zones]})


@admin_bp.post("/shipping/zones")
@role_required(UserRole.ADMIN.value)
def create_shipping_zone():
    payload = validate_delivery_zone_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    existing_name = DeliveryZone.query.filter(DeliveryZone.name.ilike(payload["name"])).first()
    if existing_name is not None:
        return validation_error({"name": "A delivery zone with this name already exists."})

    existing_city = DeliveryZone.query.filter(DeliveryZone.city.ilike(payload["city"])).first()
    if existing_city is not None:
        return validation_error({"city": "A delivery zone for this city already exists."})

    zone = DeliveryZone(**payload)
    db.session.add(zone)
    db.session.flush()
    _add_audit_log(
        action="admin.shipping_zone_created",
        entity_type="delivery_zone",
        entity_id=zone.id,
        metadata={"name": zone.name, "city": zone.city},
    )
    db.session.commit()
    return jsonify({"item": _serialize_delivery_zone(zone)}), 201


@admin_bp.patch("/shipping/zones/<int:zone_id>")
@role_required(UserRole.ADMIN.value)
def update_shipping_zone(zone_id: int):
    payload = validate_delivery_zone_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    zone = db.session.get(DeliveryZone, zone_id)
    if zone is None:
        return _not_found("Delivery zone not found.")

    if "name" in payload["provided_fields"]:
        existing_name = DeliveryZone.query.filter(
            DeliveryZone.id != zone.id,
            DeliveryZone.name.ilike(payload["name"]),
        ).first()
        if existing_name is not None:
            return validation_error({"name": "A delivery zone with this name already exists."})

    if "city" in payload["provided_fields"]:
        existing_city = DeliveryZone.query.filter(
            DeliveryZone.id != zone.id,
            DeliveryZone.city.ilike(payload["city"]),
        ).first()
        if existing_city is not None:
            return validation_error({"city": "A delivery zone for this city already exists."})

    for field in ("name", "city", "fee", "estimated_days_min", "estimated_days_max", "is_active"):
        if field in payload["provided_fields"]:
            setattr(zone, field, payload[field])

    _add_audit_log(
        action="admin.shipping_zone_updated",
        entity_type="delivery_zone",
        entity_id=zone.id,
        metadata={"name": zone.name, "city": zone.city, "is_active": zone.is_active},
    )
    db.session.commit()
    return jsonify({"item": _serialize_delivery_zone(zone)})


@admin_bp.delete("/shipping/zones/<int:zone_id>")
@role_required(UserRole.ADMIN.value)
def delete_shipping_zone(zone_id: int):
    zone = db.session.get(DeliveryZone, zone_id)
    if zone is None:
        return _not_found("Delivery zone not found.")

    order_count = Order.query.filter_by(delivery_zone_name=zone.name).count()
    if order_count:
        return validation_error({"zone": "This delivery zone is already referenced by orders and cannot be deleted."})

    _add_audit_log(
        action="admin.shipping_zone_deleted",
        entity_type="delivery_zone",
        entity_id=zone.id,
        metadata={"name": zone.name, "city": zone.city},
    )
    db.session.delete(zone)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.get("/shipping/orders")
@role_required(UserRole.ADMIN.value)
def list_shipping_orders():
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


@admin_bp.get("/vouchers")
@role_required(UserRole.ADMIN.value)
def list_vouchers():
    vouchers = PromoCode.query.order_by(PromoCode.created_at.desc(), PromoCode.id.desc()).all()
    return jsonify({"items": [_serialize_voucher(voucher) for voucher in vouchers]})


@admin_bp.post("/vouchers")
@role_required(UserRole.ADMIN.value)
def create_voucher():
    payload = validate_voucher_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    uniqueness_error = ensure_unique_promo_code(payload["code"])
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

    voucher = PromoCode(
        name=payload["name"],
        code=payload["code"],
        usage=payload["usage"],
        discount_type=PromoCodeType.FIXED,
        discount_value=0,
        minimum_order_amount=0,
        is_active=True,
        starts_at=payload["start_datetime"],
        ends_at=payload["end_datetime"],
    )
    db.session.add(voucher)
    db.session.flush()
    _add_audit_log(
        action="admin.voucher_created",
        entity_type="voucher",
        entity_id=voucher.id,
        metadata={"code": voucher.code, "usage": voucher.usage},
    )
    db.session.commit()
    return jsonify({"item": _serialize_voucher(voucher)}), 201


@admin_bp.patch("/vouchers/<int:voucher_id>")
@role_required(UserRole.ADMIN.value)
def update_voucher_detail(voucher_id: int):
    payload = validate_voucher_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")

    if "code" in payload["provided_fields"]:
        duplicate = PromoCode.query.filter(PromoCode.code == payload["code"], PromoCode.id != voucher.id).first()
        if duplicate is not None:
            return validation_error({"code": "A voucher with that code already exists."})

    field_map = {
        "name": "name",
        "code": "code",
        "usage": "usage",
        "start_datetime": "starts_at",
        "end_datetime": "ends_at",
    }
    for payload_field, model_field in field_map.items():
        if payload_field in payload["provided_fields"]:
            setattr(voucher, model_field, payload[payload_field])

    _add_audit_log(
        action="admin.voucher_updated",
        entity_type="voucher",
        entity_id=voucher.id,
        metadata={"code": voucher.code, "usage": voucher.usage},
    )
    db.session.commit()
    return jsonify({"item": _serialize_voucher(voucher)})


@admin_bp.delete("/vouchers/<int:voucher_id>")
@role_required(UserRole.ADMIN.value)
def delete_voucher_detail(voucher_id: int):
    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")

    _add_audit_log(
        action="admin.voucher_deleted",
        entity_type="voucher",
        entity_id=voucher.id,
        metadata={"code": voucher.code},
    )
    db.session.delete(voucher)
    db.session.commit()
    return jsonify({"message": "Voucher deleted successfully."})


@admin_bp.get("/vouchers/<int:voucher_id>/stats")
@role_required(UserRole.ADMIN.value)
def get_voucher_stats(voucher_id: int):
    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")
    return jsonify({"item": _serialize_voucher(voucher)})


@admin_bp.get("/vouchers/<int:voucher_id>/offers")
@role_required(UserRole.ADMIN.value)
def list_voucher_offers(voucher_id: int):
    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")
    return jsonify({"items": [_serialize_offer(offer) for offer in voucher.offers]})


@admin_bp.post("/vouchers/<int:voucher_id>/offers")
@role_required(UserRole.ADMIN.value)
def attach_voucher_offer(voucher_id: int):
    payload = validate_voucher_offer_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")

    offer = db.session.get(Offer, payload["offer_id"])
    if offer is None:
        return validation_error({"offer_id": "Selected offer was not found."})

    if all(existing.id != offer.id for existing in voucher.offers):
        voucher.offers.append(offer)

    _add_audit_log(
        action="admin.voucher_offer_attached",
        entity_type="voucher",
        entity_id=voucher.id,
        metadata={"code": voucher.code, "offer_id": offer.id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_voucher(voucher)})


@admin_bp.delete("/vouchers/<int:voucher_id>/offers")
@role_required(UserRole.ADMIN.value)
def detach_voucher_offer(voucher_id: int):
    payload = validate_voucher_offer_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    voucher = db.session.get(PromoCode, voucher_id)
    if voucher is None:
        return _not_found("Voucher not found.")

    offer = next((item for item in voucher.offers if item.id == payload["offer_id"]), None)
    if offer is None:
        return validation_error({"offer_id": "Selected offer is not linked to this voucher."})

    voucher.offers.remove(offer)
    _add_audit_log(
        action="admin.voucher_offer_detached",
        entity_type="voucher",
        entity_id=voucher.id,
        metadata={"code": voucher.code, "offer_id": offer.id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_voucher(voucher)})


@admin_bp.get("/ranges")
@role_required(UserRole.ADMIN.value)
def list_ranges():
    ranges = ProductRange.query.order_by(ProductRange.created_at.desc(), ProductRange.id.desc()).all()
    return jsonify({"items": [_serialize_range_item(item) for item in ranges]})


@admin_bp.post("/ranges")
@role_required(UserRole.ADMIN.value)
def create_range():
    payload = validate_range_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    existing = ProductRange.query.filter_by(slug=payload["slug"]).first()
    if existing is not None:
        return validation_error({"slug": "A range with that slug already exists."})

    item = ProductRange(**payload)
    db.session.add(item)
    db.session.flush()
    _add_audit_log(
        action="admin.range_created",
        entity_type="range",
        entity_id=item.id,
        metadata={"slug": item.slug, "includes_all_products": item.includes_all_products},
    )
    db.session.commit()
    return jsonify({"item": _serialize_range_item(item)}), 201


@admin_bp.patch("/ranges/<int:range_id>")
@role_required(UserRole.ADMIN.value)
def update_range_detail(range_id: int):
    payload = validate_range_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    item = db.session.get(ProductRange, range_id)
    if item is None:
        return _not_found("Range not found.")

    if "slug" in payload["provided_fields"]:
        existing = ProductRange.query.filter(ProductRange.slug == payload["slug"], ProductRange.id != item.id).first()
        if existing is not None:
            return validation_error({"slug": "A range with that slug already exists."})

    for field in ("name", "slug", "description", "is_public", "includes_all_products"):
        if field in payload["provided_fields"]:
            setattr(item, field, payload[field])

    _add_audit_log(
        action="admin.range_updated",
        entity_type="range",
        entity_id=item.id,
        metadata={"slug": item.slug, "includes_all_products": item.includes_all_products},
    )
    db.session.commit()
    return jsonify({"item": _serialize_range_item(item)})


@admin_bp.delete("/ranges/<int:range_id>")
@role_required(UserRole.ADMIN.value)
def delete_range_detail(range_id: int):
    item = db.session.get(ProductRange, range_id)
    if item is None:
        return _not_found("Range not found.")

    for condition in OfferCondition.query.filter_by(range_id=item.id).all():
        condition.range_id = None
    for benefit in OfferBenefit.query.filter_by(range_id=item.id).all():
        benefit.range_id = None

    _add_audit_log(
        action="admin.range_deleted",
        entity_type="range",
        entity_id=item.id,
        metadata={"slug": item.slug},
    )
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Range deleted successfully."})


@admin_bp.get("/ranges/<int:range_id>/products")
@role_required(UserRole.ADMIN.value)
def list_range_products(range_id: int):
    item = db.session.get(ProductRange, range_id)
    if item is None:
        return _not_found("Range not found.")

    products = Product.query.order_by(Product.created_at.desc(), Product.id.desc()).all() if item.includes_all_products else item.products
    return jsonify({"items": [_serialize_range_product(product) for product in products]})


@admin_bp.post("/ranges/<int:range_id>/products")
@role_required(UserRole.ADMIN.value)
def add_range_product(range_id: int):
    payload = validate_range_product_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    item = db.session.get(ProductRange, range_id)
    if item is None:
        return _not_found("Range not found.")

    product = db.session.get(Product, payload["product_id"])
    if product is None:
        return validation_error({"product_id": "Selected product was not found."})

    if all(existing.id != product.id for existing in item.products):
        item.products.append(product)

    _add_audit_log(
        action="admin.range_product_added",
        entity_type="range",
        entity_id=item.id,
        metadata={"slug": item.slug, "product_id": product.id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_range_item(item)})


@admin_bp.delete("/ranges/<int:range_id>/products")
@role_required(UserRole.ADMIN.value)
def remove_range_product(range_id: int):
    raw_payload = get_json_payload()
    if not raw_payload:
        product_id_value = request.args.get("product_id") or request.form.get("product_id")
        raw_payload = {"product_id": product_id_value} if product_id_value is not None else {}

    payload = validate_range_product_payload(raw_payload)
    if "errors" in payload:
        return validation_error(payload["errors"])

    item = db.session.get(ProductRange, range_id)
    if item is None:
        return _not_found("Range not found.")

    product = next((existing for existing in item.products if existing.id == payload["product_id"]), None)
    if product is None:
        if item.includes_all_products:
            return validation_error(
                {
                    "product_id": "This range includes all products automatically. Disable 'includes all products' or remove only explicitly assigned products."
                }
            )
        return validation_error({"product_id": "Selected product is not assigned to this range."})

    item.products.remove(product)
    _add_audit_log(
        action="admin.range_product_removed",
        entity_type="range",
        entity_id=item.id,
        metadata={"slug": item.slug, "product_id": product.id},
    )
    db.session.commit()
    return jsonify({"item": _serialize_range_item(item)})


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
    query = AuditLog.query

    search = str(request.args.get("q") or "").strip().lower()
    event_type = str(request.args.get("event_type") or "").strip().lower()
    actor_email = str(request.args.get("actor_email") or "").strip().lower()
    target_type = str(request.args.get("target_type") or "").strip().lower()
    target_id = str(request.args.get("target_id") or "").strip()
    path = str(request.args.get("path") or "").strip().lower()
    status = str(request.args.get("status") or "").strip().lower()
    date_from = str(request.args.get("date_from") or "").strip()
    date_to = str(request.args.get("date_to") or "").strip()

    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", default=50, type=int) or 50
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)

    if event_type:
        query = query.filter(AuditLog.action.ilike(f"%{event_type}%"))

    if target_type:
        query = query.filter(AuditLog.entity_type.ilike(f"%{target_type}%"))

    if target_id:
        try:
            query = query.filter(AuditLog.entity_id == int(target_id))
        except ValueError:
            return validation_error({"target_id": "target_id must be an integer."})

    if actor_email:
        query = query.join(AuditLog.actor_user).filter(User.email.ilike(f"%{actor_email}%"))

    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.created_at >= parsed_from)
        except ValueError:
            return validation_error({"date_from": "date_from must be a valid ISO date."})

    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.created_at <= parsed_to)
        except ValueError:
            return validation_error({"date_to": "date_to must be a valid ISO date."})

    audit_logs = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()
    items = [serialize_audit_log(audit_log) for audit_log in audit_logs]

    if search:
        items = [
            item for item in items
            if search in item["event_type"].lower()
            or search in (item["actor_email"] or "").lower()
            or search in (item["target_type"] or "").lower()
            or search in (item["target_repr"] or "").lower()
            or search in (item["message"] or "").lower()
        ]

    if path:
        items = [item for item in items if path in (item["path"] or "").lower()]

    if status:
        items = [item for item in items if (item["status"] or "").lower() == status]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = items[start:end]
    num_pages = max((total + page_size - 1) // page_size, 1)

    return jsonify({
        "results": paged_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "num_pages": num_pages,
            "has_next": page < num_pages,
        },
    })


@admin_bp.get("/audit-logs/<int:audit_log_id>")
@role_required(UserRole.ADMIN.value)
def get_audit_log_detail(audit_log_id: int):
    audit_log = db.session.get(AuditLog, audit_log_id)
    if audit_log is None:
        return _not_found("Audit log not found.")

    return jsonify({"audit_log": serialize_audit_log(audit_log)})


def _serialize_cms_page(page: CmsPage) -> dict:
    return {
        "id": page.id,
        "url": page.url,
        "page_key": page.page_key,
        "page_type": page.page_type,
        "status": page.status,
        "title": page.title,
        "excerpt": page.excerpt,
        "content": page.content,
        "meta_title": page.meta_title,
        "meta_description": page.meta_description,
        "registration_required": page.registration_required,
        "is_system_page": page.is_system_page,
        "allow_indexing": page.allow_indexing,
        "published_at": page.published_at.isoformat() if page.published_at else None,
        "created_by_user_id": page.created_by_user_id,
        "created_by_name": page.created_by_user.full_name if page.created_by_user else None,
        "updated_by_user_id": page.updated_by_user_id,
        "updated_by_name": page.updated_by_user.full_name if page.updated_by_user else None,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@admin_bp.get("/pages")
@role_required(UserRole.ADMIN.value)
def list_cms_pages():
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 200)

    page, page_error = parse_positive_int(page, field_name="page")
    if page_error:
        return validation_error(page_error)

    page_size, page_size_error = parse_positive_int(page_size, field_name="page_size")
    if page_size_error:
        return validation_error(page_size_error)

    pagination = CmsPage.query.order_by(CmsPage.is_system_page.desc(), CmsPage.title.asc(), CmsPage.id.desc()).paginate(
        page=page,
        per_page=min(page_size, 200),
        error_out=False,
    )
    return jsonify({
        "results": [_serialize_cms_page(item) for item in pagination.items],
        "pagination": {
            "page": pagination.page,
            "page_size": pagination.per_page,
            "total": pagination.total,
            "num_pages": pagination.pages,
            "has_next": pagination.has_next,
        },
    })


@admin_bp.post("/pages")
@role_required(UserRole.ADMIN.value)
def create_cms_page():
    payload = validate_cms_page_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    existing = CmsPage.query.filter_by(url=payload["url"]).first()
    if existing:
        return validation_error({"url": "A page with this URL already exists."})
    if payload["page_key"]:
        existing_by_key = CmsPage.query.filter_by(page_key=payload["page_key"]).first()
        if existing_by_key:
            return validation_error({"page_key": "A page with this page_key already exists."})

    page = CmsPage(
        url=payload["url"],
        page_key=payload["page_key"],
        page_type=payload["page_type"],
        status=payload["status"],
        title=payload["title"],
        excerpt=payload["excerpt"],
        content=payload["content"],
        meta_title=payload["meta_title"],
        meta_description=payload["meta_description"],
        registration_required=payload["registration_required"],
        is_system_page=payload["is_system_page"],
        allow_indexing=payload["allow_indexing"],
        published_at=datetime.now(timezone.utc) if payload["status"] == "published" else None,
        created_by_user_id=g.current_user.id,
        updated_by_user_id=g.current_user.id,
    )
    db.session.add(page)
    db.session.flush()
    _add_audit_log(
        action="admin.cms_page_created",
        entity_type="cms_page",
        entity_id=page.id,
        metadata={"url": page.url, "title": page.title, "page_key": page.page_key, "status": page.status},
    )
    db.session.commit()
    return jsonify({"page": _serialize_cms_page(page)}), 201


@admin_bp.get("/pages/<int:page_id>")
@role_required(UserRole.ADMIN.value)
def get_cms_page(page_id: int):
    page = db.session.get(CmsPage, page_id)
    if page is None:
        return _not_found("Page not found.")
    return jsonify({"page": _serialize_cms_page(page)})


@admin_bp.patch("/pages/<int:page_id>")
@role_required(UserRole.ADMIN.value)
def update_cms_page(page_id: int):
    page = db.session.get(CmsPage, page_id)
    if page is None:
        return _not_found("Page not found.")

    payload = validate_cms_page_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if page.is_system_page and "is_system_page" in payload["provided_fields"] and not payload["is_system_page"]:
        return validation_error({"is_system_page": "System pages cannot be downgraded from system status."})

    if "url" in payload["provided_fields"]:
        existing = CmsPage.query.filter(CmsPage.url == payload["url"], CmsPage.id != page.id).first()
        if existing:
            return validation_error({"url": "A page with this URL already exists."})
        page.url = payload["url"]
    if "page_key" in payload["provided_fields"]:
        if payload["page_key"]:
            existing = CmsPage.query.filter(CmsPage.page_key == payload["page_key"], CmsPage.id != page.id).first()
            if existing:
                return validation_error({"page_key": "A page with this page_key already exists."})
        page.page_key = payload["page_key"]
    if "page_type" in payload["provided_fields"]:
        page.page_type = payload["page_type"]
    if "status" in payload["provided_fields"]:
        previous_status = page.status
        page.status = payload["status"]
        if payload["status"] == "published" and previous_status != "published":
            page.published_at = datetime.now(timezone.utc)
    if "title" in payload["provided_fields"]:
        page.title = payload["title"]
    if "excerpt" in payload["provided_fields"]:
        page.excerpt = payload["excerpt"]
    if "content" in payload["provided_fields"]:
        page.content = payload["content"]
    if "meta_title" in payload["provided_fields"]:
        page.meta_title = payload["meta_title"]
    if "meta_description" in payload["provided_fields"]:
        page.meta_description = payload["meta_description"]
    if "registration_required" in payload["provided_fields"]:
        page.registration_required = payload["registration_required"]
    if "is_system_page" in payload["provided_fields"]:
        page.is_system_page = payload["is_system_page"]
    if "allow_indexing" in payload["provided_fields"]:
        page.allow_indexing = payload["allow_indexing"]
    page.updated_by_user_id = g.current_user.id

    _add_audit_log(
        action="admin.cms_page_updated",
        entity_type="cms_page",
        entity_id=page.id,
        metadata={"url": page.url, "title": page.title, "page_key": page.page_key, "status": page.status},
    )
    db.session.commit()
    return jsonify({"page": _serialize_cms_page(page)})


@admin_bp.delete("/pages/<int:page_id>")
@role_required(UserRole.ADMIN.value)
def delete_cms_page(page_id: int):
    page = db.session.get(CmsPage, page_id)
    if page is None:
        return _not_found("Page not found.")
    if page.is_system_page:
        return validation_error({"page": "System pages cannot be deleted. Archive them instead."})

    metadata = {"url": page.url, "title": page.title, "page_key": page.page_key}
    db.session.delete(page)
    _add_audit_log(
        action="admin.cms_page_deleted",
        entity_type="cms_page",
        entity_id=page_id,
        metadata=metadata,
    )
    db.session.commit()
    return jsonify({"message": "Page deleted successfully."})


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
    payload = validate_banner_payload(get_json_payload())
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


@admin_bp.patch("/banners/<int:banner_id>")
@role_required(UserRole.ADMIN.value)
def update_banner_detail(banner_id: int):
    payload = validate_banner_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    banner, error = update_banner(banner_id=banner_id, payload=payload)
    if error:
        return _not_found("Banner not found.")

    _add_audit_log(
        action="admin.banner_updated",
        entity_type="banner",
        entity_id=banner.id,
        metadata={"title": banner.title, "placement": banner.placement},
    )
    db.session.commit()
    return jsonify({"item": serialize_banner(banner)})


@admin_bp.delete("/banners/<int:banner_id>")
@role_required(UserRole.ADMIN.value)
def remove_banner(banner_id: int):
    banner, error = delete_banner(banner_id=banner_id)
    if error:
        return _not_found("Banner not found.")

    _add_audit_log(
        action="admin.banner_deleted",
        entity_type="banner",
        entity_id=banner.id,
        metadata={"title": banner.title},
    )
    db.session.commit()
    return jsonify({"message": "Banner deleted successfully."})


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
    payload = validate_promo_code_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    uniqueness_error = ensure_unique_promo_code(payload["code"])
    if uniqueness_error:
        return validation_error(uniqueness_error.details)

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


@admin_bp.patch("/promo-codes/<int:promo_code_id>")
@role_required(UserRole.ADMIN.value)
def update_promo_code_detail(promo_code_id: int):
    payload = validate_promo_code_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if "discount_type" in payload.get("provided_fields", set()):
        payload["discount_type"] = PromoCodeType(payload["discount_type"])

    promo_code, error = update_promo_code(promo_code_id=promo_code_id, payload=payload)
    if error:
        if error.status_code == 404:
            return _not_found("Promo code not found.")
        return validation_error(error.details)

    _add_audit_log(
        action="admin.promo_code_updated",
        entity_type="promo_code",
        entity_id=promo_code.id,
        metadata={"code": promo_code.code, "is_active": promo_code.is_active},
    )
    db.session.commit()
    return jsonify({"item": serialize_promo_code(promo_code)})


@admin_bp.delete("/promo-codes/<int:promo_code_id>")
@role_required(UserRole.ADMIN.value)
def remove_promo_code(promo_code_id: int):
    promo_code, error = delete_promo_code(promo_code_id=promo_code_id)
    if error:
        return _not_found("Promo code not found.")

    _add_audit_log(
        action="admin.promo_code_deleted",
        entity_type="promo_code",
        entity_id=promo_code.id,
        metadata={"code": promo_code.code},
    )
    db.session.commit()
    return jsonify({"message": "Promo code deleted successfully."})


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
    payload = validate_flash_sale_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    product, product_error = get_product_for_flash_sale(payload["product_id"])
    if product_error:
        return validation_error(product_error.details)

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


@admin_bp.patch("/flash-sales/<int:flash_sale_id>")
@role_required(UserRole.ADMIN.value)
def update_flash_sale_detail(flash_sale_id: int):
    payload = validate_flash_sale_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if "product_id" in payload.get("provided_fields", set()):
        product, product_error = get_product_for_flash_sale(payload["product_id"])
        if product_error:
            return validation_error(product_error.details)
        payload["product_id"] = product.id

    flash_sale, error = update_flash_sale(flash_sale_id=flash_sale_id, payload=payload)
    if error:
        return _not_found("Flash sale not found.")

    _add_audit_log(
        action="admin.flash_sale_updated",
        entity_type="flash_sale",
        entity_id=flash_sale.id,
        metadata={"title": flash_sale.title, "product_id": flash_sale.product_id},
    )
    db.session.commit()
    return jsonify({"item": serialize_flash_sale(flash_sale)})


@admin_bp.delete("/flash-sales/<int:flash_sale_id>")
@role_required(UserRole.ADMIN.value)
def remove_flash_sale(flash_sale_id: int):
    flash_sale, error = delete_flash_sale(flash_sale_id=flash_sale_id)
    if error:
        return _not_found("Flash sale not found.")

    _add_audit_log(
        action="admin.flash_sale_deleted",
        entity_type="flash_sale",
        entity_id=flash_sale.id,
        metadata={"title": flash_sale.title},
    )
    db.session.commit()
    return jsonify({"message": "Flash sale deleted successfully."})


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
    payload = validate_order_status_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    order = db.session.get(Order, order_id)
    if order is None:
        return _not_found("Order not found.")

    transition_error = transition_order(order, OrderStatus(payload["status"]))
    if transition_error is not None:
        return (
            jsonify(
                {
                    "error": {
                        "code": transition_error.code,
                        "message": transition_error.message,
                    }
                }
            ),
            400,
        )
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
    payload = validate_refund_status_payload(get_json_payload())
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
    notify_refund_updated(refund)
    db.session.commit()
    return jsonify({"item": serialize_refund(refund)})


@admin_bp.get("/partners")
@role_required(UserRole.ADMIN.value)
def list_partners():
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 200)

    page, page_error = parse_positive_int(page, field_name="page")
    if page_error:
        return validation_error(page_error)

    page_size, page_size_error = parse_positive_int(page_size, field_name="page_size")
    if page_size_error:
        return validation_error(page_size_error)

    query = Partner.query.order_by(Partner.name.asc(), Partner.id.asc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [_serialize_partner(partner) for partner in pagination.items]
    return jsonify(
        {
            "results": items,
            "pagination": {
                "page": pagination.page,
                "page_size": pagination.per_page,
                "total": pagination.total,
                "num_pages": pagination.pages,
                "has_next": pagination.has_next,
            },
        }
    )


@admin_bp.post("/partners")
@role_required(UserRole.ADMIN.value)
def create_partner():
    payload = validate_partner_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    existing_name = Partner.query.filter(Partner.name.ilike(payload["name"])).first()
    if existing_name:
        return validation_error({"name": "A partner with this name already exists."})

    if payload["code"]:
        existing_code = Partner.query.filter(Partner.code.ilike(payload["code"])).first()
        if existing_code:
            return validation_error({"code": "A partner with this code already exists."})

    partner = Partner(name=payload["name"], code=payload["code"])
    db.session.add(partner)
    db.session.flush()
    _add_audit_log(
        action="admin.partner_created",
        entity_type="partner",
        entity_id=partner.id,
        metadata={"name": partner.name, "code": partner.code},
    )
    db.session.commit()
    return jsonify({"partner": _serialize_partner(partner)}), 201


@admin_bp.patch("/partners/<int:partner_id>")
@role_required(UserRole.ADMIN.value)
def update_partner(partner_id: int):
    partner = db.session.get(Partner, partner_id)
    if partner is None:
        return _not_found("Partner not found.")

    payload = validate_partner_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if "name" in payload["provided_fields"]:
        existing_name = (
            Partner.query.filter(Partner.id != partner.id, Partner.name.ilike(payload["name"])).first()
        )
        if existing_name:
            return validation_error({"name": "A partner with this name already exists."})
        partner.name = payload["name"]

    if "code" in payload["provided_fields"]:
        if payload["code"]:
            existing_code = (
                Partner.query.filter(Partner.id != partner.id, Partner.code.ilike(payload["code"])).first()
            )
            if existing_code:
                return validation_error({"code": "A partner with this code already exists."})
        partner.code = payload["code"]

    _add_audit_log(
        action="admin.partner_updated",
        entity_type="partner",
        entity_id=partner.id,
        metadata={"name": partner.name, "code": partner.code},
    )
    db.session.commit()
    return jsonify({"partner": _serialize_partner(partner)})


@admin_bp.delete("/partners/<int:partner_id>")
@role_required(UserRole.ADMIN.value)
def delete_partner(partner_id: int):
    partner = db.session.get(Partner, partner_id)
    if partner is None:
        return _not_found("Partner not found.")

    if partner.users:
        return validation_error({"partner": "Unlink all users before deleting this partner."})

    metadata = {"name": partner.name, "code": partner.code}
    db.session.delete(partner)
    _add_audit_log(
        action="admin.partner_deleted",
        entity_type="partner",
        entity_id=partner_id,
        metadata=metadata,
    )
    db.session.commit()
    return jsonify({"message": "Partner deleted successfully."})


@admin_bp.get("/partners/<int:partner_id>/users")
@role_required(UserRole.ADMIN.value)
def list_partner_users(partner_id: int):
    partner = db.session.get(Partner, partner_id)
    if partner is None:
        return _not_found("Partner not found.")

    users = sorted(partner.users, key=lambda user: (user.full_name.lower(), user.id))
    return jsonify({"results": [_serialize_partner_user(user) for user in users]})


@admin_bp.post("/partners/<int:partner_id>/users/<int:user_id>/link")
@role_required(UserRole.ADMIN.value)
def link_partner_user(partner_id: int, user_id: int):
    partner = db.session.get(Partner, partner_id)
    if partner is None:
        return _not_found("Partner not found.")

    user = db.session.get(User, user_id)
    if user is None:
        return _not_found("User not found.")

    if all(existing_user.id != user.id for existing_user in partner.users):
        partner.users.append(user)

    _add_audit_log(
        action="admin.partner_user_linked",
        entity_type="partner",
        entity_id=partner.id,
        metadata={"user_id": user.id, "user_email": user.email},
    )
    db.session.commit()
    return jsonify({"partner": _serialize_partner(partner)})


@admin_bp.delete("/partners/<int:partner_id>/users/<int:user_id>/unlink")
@role_required(UserRole.ADMIN.value)
def unlink_partner_user(partner_id: int, user_id: int):
    partner = db.session.get(Partner, partner_id)
    if partner is None:
        return _not_found("Partner not found.")

    user = db.session.get(User, user_id)
    if user is None:
        return _not_found("User not found.")

    if all(existing_user.id != user.id for existing_user in partner.users):
        return validation_error({"user": "Selected user is not linked to this partner."})

    partner.users = [existing_user for existing_user in partner.users if existing_user.id != user.id]
    _add_audit_log(
        action="admin.partner_user_unlinked",
        entity_type="partner",
        entity_id=partner.id,
        metadata={"user_id": user.id, "user_email": user.email},
    )
    db.session.commit()
    return jsonify({"partner": _serialize_partner(partner)})


@admin_bp.get("/suppliers")
@role_required(UserRole.ADMIN.value)
def list_suppliers():
    status_filter = str(request.args.get("status", "")).strip().lower()
    query = Supplier.query.order_by(Supplier.created_at.desc(), Supplier.id.desc())
    if status_filter:
        allowed_statuses = {status.value for status in SupplierStatus}
        if status_filter not in allowed_statuses:
            return validation_error({"status": "status must be a supported supplier status."})
        query = query.filter(Supplier.status == SupplierStatus(status_filter))
    return jsonify({"results": [_serialize_supplier(supplier) for supplier in query.all()]})


@admin_bp.post("/suppliers")
@role_required(UserRole.ADMIN.value)
def create_supplier():
    payload = validate_supplier_create_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = db.session.get(User, payload["user_id"])
    if user is None:
        return validation_error({"user_id": "Selected user was not found."})

    if Supplier.query.filter_by(user_id=user.id).first() is not None:
        return validation_error({"user_id": "This user already has a supplier profile."})

    partner = None
    if payload["partner_id"] is not None:
        partner = db.session.get(Partner, payload["partner_id"])
        if partner is None:
            return validation_error({"partner_id": "Selected partner was not found."})

    supplier = Supplier(
        user_id=user.id,
        partner_id=partner.id if partner else None,
        company_name=payload["company_name"],
        contact_name=payload["contact_name"],
        phone=payload["phone"],
        country_code=payload["country_code"],
        website=payload["website"],
        notes=payload["notes"],
        status=SupplierStatus(payload["status"]),
    )
    db.session.add(supplier)
    db.session.flush()
    _add_audit_log(
        action="admin.supplier_created",
        entity_type="supplier",
        entity_id=supplier.id,
        metadata={
            "company_name": supplier.company_name,
            "status": supplier.status.value if hasattr(supplier.status, "value") else supplier.status,
            "partner_id": supplier.partner_id,
            "user_id": supplier.user_id,
        },
    )
    db.session.commit()
    return jsonify({"supplier": _serialize_supplier(supplier)}), 201


@admin_bp.get("/suppliers/<int:supplier_id>")
@role_required(UserRole.ADMIN.value)
def get_supplier(supplier_id: int):
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return _not_found("Supplier not found.")
    return jsonify({"supplier": _serialize_supplier(supplier)})


@admin_bp.patch("/suppliers/<int:supplier_id>")
@role_required(UserRole.ADMIN.value)
def update_supplier(supplier_id: int):
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        return _not_found("Supplier not found.")

    payload = validate_supplier_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if "status" in payload["provided_fields"]:
        supplier.status = SupplierStatus(payload["status"])
    if "company_name" in payload["provided_fields"]:
        supplier.company_name = payload["company_name"]
    if "contact_name" in payload["provided_fields"]:
        supplier.contact_name = payload["contact_name"]
    if "phone" in payload["provided_fields"]:
        supplier.phone = payload["phone"]
    if "country_code" in payload["provided_fields"]:
        supplier.country_code = payload["country_code"]
    if "website" in payload["provided_fields"]:
        supplier.website = payload["website"]
    if "notes" in payload["provided_fields"]:
        supplier.notes = payload["notes"]

    _add_audit_log(
        action="admin.supplier_updated",
        entity_type="supplier",
        entity_id=supplier.id,
        metadata={
            "company_name": supplier.company_name,
            "status": supplier.status.value if hasattr(supplier.status, "value") else supplier.status,
            "partner_id": supplier.partner_id,
            "user_id": supplier.user_id,
        },
    )
    db.session.commit()
    return jsonify({"supplier": _serialize_supplier(supplier)})


@admin_bp.get("/integrations")
@role_required(UserRole.ADMIN.value)
def list_integrations():
    return jsonify({"results": list_all_connections()})


def _parse_integration_id(raw_connection_id: str):
    try:
        return int(raw_connection_id)
    except (TypeError, ValueError):
        return None


@admin_bp.post("/integrations")
@role_required(UserRole.ADMIN.value)
def create_integration():
    payload = validate_integration_connection_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    partner = None
    if payload["partner_id"] is not None:
        partner = db.session.get(Partner, payload["partner_id"])
        if partner is None:
            return validation_error({"partner_id": "Selected partner was not found."})

    connection = IntegrationConnection(
        name=payload["name"],
        partner_id=partner.id if partner else None,
        connection_type=payload["connection_type"],
        base_url=payload["base_url"],
        auth_type=payload["auth_type"],
        credential_source=payload["credential_source"],
        secret_env_prefix=payload["secret_env_prefix"],
        credential_values=payload["credential_values"],
        default_company=payload["default_company"],
        default_warehouse=payload["default_warehouse"],
        poll_interval_minutes=payload["poll_interval_minutes"],
        status=payload["status"],
        is_active=payload["is_active"],
    )
    db.session.add(connection)
    db.session.flush()
    _add_audit_log(
        action="admin.integration_created",
        entity_type="integration_connection",
        entity_id=connection.id,
        metadata={"name": connection.name, "connection_type": connection.connection_type},
    )
    db.session.commit()
    return jsonify({"item": serialize_integration_connection(connection)}), 201


@admin_bp.get("/integrations/<connection_id>")
@role_required(UserRole.ADMIN.value)
def get_integration(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")

    payload = get_connection_payload(connection_id)
    if payload is None:
        return _not_found("Integration connection not found.")

    return jsonify({"item": payload})


@admin_bp.patch("/integrations/<connection_id>")
@role_required(UserRole.ADMIN.value)
def update_integration(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    connection = db.session.get(IntegrationConnection, connection_id)
    if connection is None:
        return _not_found("Integration connection not found.")

    payload = validate_integration_connection_update_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    if "partner_id" in payload["provided_fields"]:
        if payload["partner_id"] is None:
            connection.partner_id = None
        else:
            partner = db.session.get(Partner, payload["partner_id"])
            if partner is None:
                return validation_error({"partner_id": "Selected partner was not found."})
            connection.partner_id = partner.id

    for field in (
        "name",
        "connection_type",
        "base_url",
        "auth_type",
        "credential_source",
        "secret_env_prefix",
        "credential_values",
        "default_company",
        "default_warehouse",
        "poll_interval_minutes",
        "status",
        "is_active",
    ):
        if field in payload["provided_fields"]:
            setattr(connection, field, payload[field])

    _add_audit_log(
        action="admin.integration_updated",
        entity_type="integration_connection",
        entity_id=connection.id,
        metadata={"name": connection.name, "connection_type": connection.connection_type},
    )
    db.session.commit()
    return jsonify({"item": serialize_integration_connection(connection)})


@admin_bp.delete("/integrations/<connection_id>")
@role_required(UserRole.ADMIN.value)
def delete_integration(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    connection = db.session.get(IntegrationConnection, connection_id)
    if connection is None:
        return _not_found("Integration connection not found.")

    metadata = {"name": connection.name, "connection_type": connection.connection_type}
    IntegrationLog.query.filter_by(connection_id=connection.id).delete()
    db.session.delete(connection)
    _add_audit_log(
        action="admin.integration_deleted",
        entity_type="integration_connection",
        entity_id=connection_id,
        metadata=metadata,
    )
    db.session.commit()
    return jsonify({"message": "Integration deleted successfully."})


@admin_bp.get("/integrations/<connection_id>/logs")
@role_required(UserRole.ADMIN.value)
def list_integration_logs(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    payload = get_connection_payload(connection_id)
    if payload is None:
        return _not_found("Integration connection not found.")

    logs = (
        IntegrationLog.query.filter_by(connection_id=connection_id)
        .order_by(IntegrationLog.created_at.desc(), IntegrationLog.id.desc())
        .limit(100)
        .all()
    )
    return jsonify(
        {
            "results": [
                {
                    "id": log.id,
                    "connection": log.connection_id,
                    "connection_name": log.connection_name,
                    "direction": log.direction,
                    "entity_type": log.entity_type,
                    "external_reference": log.external_reference or "",
                    "status": log.status,
                    "payload_excerpt": log.payload_excerpt or {},
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        }
    )


@admin_bp.post("/integrations/<connection_id>/test")
@role_required(UserRole.ADMIN.value)
def test_integration(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    adapter = get_connection_adapter(connection_id)
    if adapter is None:
        return _not_found("Integration connection not found.")

    ok, result = adapter.test_connection()
    adapter.on_test_result(ok=ok)
    adapter.persist_state()
    append_integration_log(
        connection_id=connection_id,
        connection_name=adapter.name,
        direction="outbound",
        entity_type="connection_test",
        external_reference=adapter.connection_type,
        status="success" if ok else "error",
        payload_excerpt=result,
        error_message=None if ok else "Local validation failed.",
    )
    db.session.commit()
    return jsonify({"result": {"ok": ok, **result}})


@admin_bp.get("/integrations/<connection_id>/preview")
@role_required(UserRole.ADMIN.value)
def preview_integration(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    adapter = get_connection_adapter(connection_id)
    if adapter is None:
        return _not_found("Integration connection not found.")
    if not adapter.supports_preview:
        return validation_error({"integration": "This connection type does not support preview."})

    resource = str(request.args.get("resource", "items")).strip().lower()
    limit_raw = request.args.get("limit", 20)
    limit, limit_error = parse_positive_int(limit_raw, field_name="limit")
    if limit_error:
        return validation_error(limit_error)

    preview = adapter.preview_catalog_records(resource, min(limit, 100))
    append_integration_log(
        connection_id=connection_id,
        connection_name=adapter.name,
        direction="inbound",
        entity_type=f"{resource}_preview",
        external_reference=adapter.connection_type,
        status="success",
        payload_excerpt={"count": preview["count"], "resource": resource},
    )
    db.session.commit()
    return jsonify(preview)


@admin_bp.post("/integrations/<connection_id>/import")
@role_required(UserRole.ADMIN.value)
def import_integration_catalog(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    adapter = get_connection_adapter(connection_id)
    if adapter is None:
        return _not_found("Integration connection not found.")
    if not adapter.supports_import:
        return validation_error({"integration": "This connection type does not support import."})

    include_stock = bool(get_json_payload().get("include_stock", False))
    summary = adapter.import_catalog(include_stock=include_stock)
    adapter.on_import_success()
    adapter.persist_state()
    append_integration_log(
        connection_id=connection_id,
        connection_name=adapter.name,
        direction="inbound",
        entity_type="catalog_import",
        external_reference=adapter.connection_type,
        status="success",
        payload_excerpt=summary,
    )
    db.session.commit()
    return jsonify({"summary": summary})


@admin_bp.post("/integrations/<connection_id>/stock-sync")
@role_required(UserRole.ADMIN.value)
def sync_integration_stock(connection_id: str):
    connection_id = _parse_integration_id(connection_id)
    if connection_id is None:
        return _not_found("Integration connection not found.")
    adapter = get_connection_adapter(connection_id)
    if adapter is None:
        return _not_found("Integration connection not found.")
    if not adapter.supports_stock_sync:
        return validation_error({"integration": "This connection type does not support stock sync."})

    summary = adapter.sync_stock()
    adapter.on_stock_sync_success()
    adapter.persist_state()
    append_integration_log(
        connection_id=connection_id,
        connection_name=adapter.name,
        direction="sync",
        entity_type="stock_sync",
        external_reference=adapter.connection_type,
        status="success",
        payload_excerpt=summary,
    )
    db.session.commit()
    return jsonify({"summary": summary})
