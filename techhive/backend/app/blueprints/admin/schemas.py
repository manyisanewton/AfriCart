from datetime import datetime

from app.models import OrderStatus, RefundStatus, UserRole, VendorKYCStatus, VendorStatus


def validate_role_payload(payload: dict | None) -> dict:
    data = payload or {}
    role = str(data.get("role", "")).strip().lower()
    allowed_roles = {role.value for role in UserRole}
    if role not in allowed_roles:
        return {"errors": {"role": "role must be a supported user role."}}
    return {"role": role}


def validate_vendor_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {status.value for status in VendorStatus}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be a supported vendor status."}}
    return {"status": status}


def validate_named_entity_payload(payload: dict | None) -> dict:
    data = payload or {}
    name = str(data.get("name", "")).strip()
    slug = str(data.get("slug", "")).strip()
    if not name:
        return {"errors": {"name": "name is required."}}
    if not slug:
        return {"errors": {"slug": "slug is required."}}
    return {
        "name": name,
        "slug": slug,
        "description": str(data.get("description") or "").strip() or None,
        "website_url": str(data.get("website_url") or "").strip() or None,
        "logo_url": str(data.get("logo_url") or "").strip() or None,
    }


def validate_product_active_payload(payload: dict | None) -> dict:
    data = payload or {}
    if "is_active" not in data:
        return {"errors": {"is_active": "is_active is required."}}
    return {"is_active": bool(data.get("is_active"))}


def validate_order_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {status.value for status in OrderStatus}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be a supported order status."}}
    return {"status": status}


def validate_promo_code_payload(payload: dict | None) -> dict:
    data = payload or {}
    code = str(data.get("code", "")).strip().upper()
    discount_type = str(data.get("discount_type", "")).strip().lower()
    errors = {}

    if not code:
        errors["code"] = "code is required."
    if discount_type not in {"percentage", "fixed"}:
        errors["discount_type"] = "discount_type must be percentage or fixed."

    try:
        discount_value = float(data.get("discount_value"))
        if discount_value <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["discount_value"] = "discount_value must be a positive number."

    try:
        minimum_order_amount = float(data.get("minimum_order_amount", 0))
        if minimum_order_amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["minimum_order_amount"] = "minimum_order_amount must be a non-negative number."

    if errors:
        return {"errors": errors}

    return {
        "code": code,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "minimum_order_amount": minimum_order_amount,
        "is_active": bool(data.get("is_active", True)),
    }


def validate_refund_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {status.value for status in RefundStatus}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be a supported refund status."}}
    return {
        "status": status,
        "admin_note": str(data.get("admin_note") or "").strip() or None,
    }


def validate_vendor_kyc_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {
        VendorKYCStatus.PENDING.value,
        VendorKYCStatus.APPROVED.value,
        VendorKYCStatus.REJECTED.value,
    }
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be pending, approved, or rejected."}}
    return {
        "status": status,
        "admin_note": str(data.get("admin_note") or "").strip() or None,
    }


def validate_banner_payload(payload: dict | None) -> dict:
    data = payload or {}
    title = str(data.get("title", "")).strip()
    image_url = str(data.get("image_url", "")).strip()
    errors = {}

    if not title:
        errors["title"] = "title is required."
    if not image_url:
        errors["image_url"] = "image_url is required."

    try:
        sort_order = int(data.get("sort_order", 0))
    except (TypeError, ValueError):
        errors["sort_order"] = "sort_order must be an integer."
        sort_order = 0

    if errors:
        return {"errors": errors}

    return {
        "title": title,
        "subtitle": str(data.get("subtitle") or "").strip() or None,
        "image_url": image_url,
        "link_url": str(data.get("link_url") or "").strip() or None,
        "placement": str(data.get("placement") or "homepage").strip() or "homepage",
        "sort_order": sort_order,
        "is_active": bool(data.get("is_active", True)),
    }


def validate_flash_sale_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    title = str(data.get("title", "")).strip()
    if not title:
        errors["title"] = "title is required."

    try:
        product_id = int(data.get("product_id"))
    except (TypeError, ValueError):
        errors["product_id"] = "product_id must be a valid integer."
        product_id = None

    try:
        sale_price = float(data.get("sale_price"))
        if sale_price <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["sale_price"] = "sale_price must be a positive number."
        sale_price = None

    try:
        starts_at = datetime.fromisoformat(str(data.get("starts_at", "")).strip())
    except (TypeError, ValueError):
        errors["starts_at"] = "starts_at must be a valid ISO datetime."
        starts_at = None

    try:
        ends_at = datetime.fromisoformat(str(data.get("ends_at", "")).strip())
    except (TypeError, ValueError):
        errors["ends_at"] = "ends_at must be a valid ISO datetime."
        ends_at = None

    if starts_at and ends_at and starts_at >= ends_at:
        errors["ends_at"] = "ends_at must be after starts_at."

    if errors:
        return {"errors": errors}

    return {
        "title": title,
        "product_id": product_id,
        "sale_price": sale_price,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "is_active": bool(data.get("is_active", True)),
    }
