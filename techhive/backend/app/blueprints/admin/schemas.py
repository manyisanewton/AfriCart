from datetime import datetime

from app.models import (
    OrderStatus,
    RefundStatus,
    SupportTicketStatus,
    UserRole,
    VendorKYCStatus,
    VendorStatus,
)


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


def validate_platform_setting_payload(payload: dict | None) -> dict:
    data = payload or {}
    key = str(data.get("key", "")).strip()
    value = data.get("value")
    if not key:
        return {"errors": {"key": "key is required."}}
    if value in (None, ""):
        return {"errors": {"value": "value is required."}}
    return {
        "key": key,
        "value": str(value),
        "description": str(data.get("description") or "").strip() or None,
        "is_public": bool(data.get("is_public", False)),
    }


def validate_platform_setting_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    field_names = {"value", "description", "is_public"}
    provided_fields = {field for field in field_names if field in data}
    if not provided_fields:
        return {"errors": {"setting": "At least one setting field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    if "value" in provided_fields:
        if data.get("value") in (None, ""):
            return {"errors": {"value": "value is required."}}
        normalized["value"] = str(data.get("value"))
    if "description" in provided_fields:
        normalized["description"] = str(data.get("description") or "").strip() or None
    if "is_public" in provided_fields:
        normalized["is_public"] = bool(data.get("is_public"))
    return normalized


def validate_recommendation_settings_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {
        "popularity_blend_weight",
        "trending_window_days",
        "trending_reason_threshold",
        "max_brand_recommendations",
        "max_vendor_recommendations",
        "max_category_recommendations",
    }
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"settings": "At least one recommendation setting must be provided."}}

    errors = {}
    normalized = {}
    for field in provided_fields:
        value = data.get(field)
        try:
            if field in {"trending_window_days", "max_brand_recommendations", "max_vendor_recommendations", "max_category_recommendations"}:
                normalized[field] = int(value)
            else:
                normalized[field] = float(value)
        except (TypeError, ValueError):
            errors[field] = f"{field} must be numeric."

    if errors:
        return {"errors": errors}
    return normalized


def validate_support_ticket_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {member.value for member in SupportTicketStatus}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be a supported support ticket status."}}
    return {
        "status": status,
        "admin_note": str(data.get("admin_note") or "").strip() or None,
    }


def validate_notification_delivery_retry_payload(payload: dict | None) -> dict:
    data = payload or {}
    delivery_id = data.get("delivery_id")
    try:
        delivery_id = int(delivery_id)
        if delivery_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"delivery_id": "delivery_id must be a positive integer."}}
    return {"delivery_id": delivery_id}


def validate_bulk_notification_payload(payload: dict | None) -> dict:
    data = payload or {}
    title = str(data.get("title", "")).strip()
    message = str(data.get("message", "")).strip()
    channels_raw = data.get("channels") or []
    errors = {}

    if not title:
        errors["title"] = "title is required."
    if not message:
        errors["message"] = "message is required."
    if not isinstance(channels_raw, list) or not channels_raw:
        errors["channels"] = "channels must be a non-empty list."

    allowed_channels = {"in_app", "email", "sms"}
    channels = []
    for channel in channels_raw if isinstance(channels_raw, list) else []:
        normalized = str(channel).strip().lower()
        if normalized not in allowed_channels:
            errors["channels"] = "channels may only include in_app, email, or sms."
            break
        channels.append(normalized)

    role = str(data.get("role") or "").strip().lower() or None
    if role is not None:
        allowed_roles = {member.value for member in UserRole}
        if role not in allowed_roles:
            errors["role"] = "role must be a supported user role."

    user_ids = data.get("user_ids")
    normalized_user_ids = None
    if user_ids is not None:
        if not isinstance(user_ids, list) or not user_ids:
            errors["user_ids"] = "user_ids must be a non-empty list."
        else:
            normalized_user_ids = []
            for value in user_ids:
                try:
                    user_id = int(value)
                    if user_id <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors["user_ids"] = "user_ids must contain positive integers."
                    break
                normalized_user_ids.append(user_id)

    if errors:
        return {"errors": errors}

    return {
        "title": title,
        "message": message,
        "subject": str(data.get("subject") or "").strip() or title,
        "channels": list(dict.fromkeys(channels)),
        "role": role,
        "user_ids": normalized_user_ids,
        "sms_message": str(data.get("sms_message") or "").strip() or message,
        "is_marketing": bool(data.get("is_marketing", False)),
    }


def validate_bulk_email_payload(payload: dict | None) -> dict:
    data = payload or {}
    subject = str(data.get("subject", "")).strip()
    headline = str(data.get("headline") or "").strip() or subject
    message = str(data.get("message", "")).strip()
    errors = {}

    if not subject:
        errors["subject"] = "subject is required."
    if not message:
        errors["message"] = "message is required."

    role = str(data.get("role") or "").strip().lower() or None
    if role is not None:
        allowed_roles = {member.value for member in UserRole}
        if role not in allowed_roles:
            errors["role"] = "role must be a supported user role."

    user_ids = data.get("user_ids")
    normalized_user_ids = None
    if user_ids is not None:
        if not isinstance(user_ids, list) or not user_ids:
            errors["user_ids"] = "user_ids must be a non-empty list."
        else:
            normalized_user_ids = []
            for value in user_ids:
                try:
                    user_id = int(value)
                    if user_id <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors["user_ids"] = "user_ids must contain positive integers."
                    break
                normalized_user_ids.append(user_id)

    cta_label = str(data.get("cta_label") or "").strip() or None
    cta_url = str(data.get("cta_url") or "").strip() or None
    if bool(cta_label) != bool(cta_url):
        errors["cta"] = "cta_label and cta_url must be provided together."

    if errors:
        return {"errors": errors}

    return {
        "subject": subject,
        "headline": headline,
        "message": message,
        "preheader": str(data.get("preheader") or "").strip() or message,
        "role": role,
        "user_ids": normalized_user_ids,
        "is_marketing": bool(data.get("is_marketing", False)),
        "cta_label": cta_label,
        "cta_url": cta_url,
        "dry_run": bool(data.get("dry_run", False)),
    }


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


def validate_named_entity_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "slug", "description", "website_url", "logo_url", "is_active"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}

    if not provided_fields:
        return {"errors": {"resource": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "name" in provided_fields:
        name = str(data.get("name", "")).strip()
        if not name:
            errors["name"] = "name cannot be blank."
        else:
            normalized["name"] = name

    if "slug" in provided_fields:
        slug = str(data.get("slug", "")).strip()
        if not slug:
            errors["slug"] = "slug cannot be blank."
        else:
            normalized["slug"] = slug

    if "description" in provided_fields:
        normalized["description"] = str(data.get("description") or "").strip() or None

    if "website_url" in provided_fields:
        normalized["website_url"] = str(data.get("website_url") or "").strip() or None

    if "logo_url" in provided_fields:
        normalized["logo_url"] = str(data.get("logo_url") or "").strip() or None

    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    if errors:
        return {"errors": errors}
    return normalized


def validate_product_active_payload(payload: dict | None) -> dict:
    data = payload or {}
    if "is_active" not in data:
        return {"errors": {"is_active": "is_active is required."}}
    return {"is_active": bool(data.get("is_active"))}


def validate_user_active_payload(payload: dict | None) -> dict:
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


def validate_banner_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {
        "title",
        "subtitle",
        "image_url",
        "link_url",
        "placement",
        "sort_order",
        "is_active",
    }
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}
    if not provided_fields:
        return {"errors": {"banner": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "title" in provided_fields:
        title = str(data.get("title", "")).strip()
        if not title:
            errors["title"] = "title cannot be blank."
        else:
            normalized["title"] = title

    if "image_url" in provided_fields:
        image_url = str(data.get("image_url", "")).strip()
        if not image_url:
            errors["image_url"] = "image_url cannot be blank."
        else:
            normalized["image_url"] = image_url

    if "subtitle" in provided_fields:
        normalized["subtitle"] = str(data.get("subtitle") or "").strip() or None
    if "link_url" in provided_fields:
        normalized["link_url"] = str(data.get("link_url") or "").strip() or None
    if "placement" in provided_fields:
        normalized["placement"] = str(data.get("placement") or "").strip() or "homepage"
    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    if "sort_order" in provided_fields:
        try:
            normalized["sort_order"] = int(data.get("sort_order"))
        except (TypeError, ValueError):
            errors["sort_order"] = "sort_order must be an integer."

    if errors:
        return {"errors": errors}
    return normalized


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


def validate_flash_sale_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"title", "product_id", "sale_price", "starts_at", "ends_at", "is_active"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}
    if not provided_fields:
        return {"errors": {"flash_sale": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "title" in provided_fields:
        title = str(data.get("title", "")).strip()
        if not title:
            errors["title"] = "title cannot be blank."
        else:
            normalized["title"] = title

    if "product_id" in provided_fields:
        try:
            product_id = int(data.get("product_id"))
            if product_id <= 0:
                raise ValueError
            normalized["product_id"] = product_id
        except (TypeError, ValueError):
            errors["product_id"] = "product_id must be a valid integer."

    if "sale_price" in provided_fields:
        try:
            sale_price = float(data.get("sale_price"))
            if sale_price <= 0:
                raise ValueError
            normalized["sale_price"] = sale_price
        except (TypeError, ValueError):
            errors["sale_price"] = "sale_price must be a positive number."

    if "starts_at" in provided_fields:
        try:
            normalized["starts_at"] = datetime.fromisoformat(str(data.get("starts_at", "")).strip())
        except (TypeError, ValueError):
            errors["starts_at"] = "starts_at must be a valid ISO datetime."

    if "ends_at" in provided_fields:
        try:
            normalized["ends_at"] = datetime.fromisoformat(str(data.get("ends_at", "")).strip())
        except (TypeError, ValueError):
            errors["ends_at"] = "ends_at must be a valid ISO datetime."

    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    starts_at = normalized.get("starts_at")
    ends_at = normalized.get("ends_at")
    if starts_at and ends_at and starts_at >= ends_at:
        errors["ends_at"] = "ends_at must be after starts_at."

    if errors:
        return {"errors": errors}
    return normalized


def validate_promo_code_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {
        "code",
        "discount_type",
        "discount_value",
        "minimum_order_amount",
        "is_active",
    }
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}
    if not provided_fields:
        return {"errors": {"promo_code": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "code" in provided_fields:
        code = str(data.get("code", "")).strip().upper()
        if not code:
            errors["code"] = "code cannot be blank."
        else:
            normalized["code"] = code

    if "discount_type" in provided_fields:
        discount_type = str(data.get("discount_type", "")).strip().lower()
        if discount_type not in {"percentage", "fixed"}:
            errors["discount_type"] = "discount_type must be percentage or fixed."
        else:
            normalized["discount_type"] = discount_type

    if "discount_value" in provided_fields:
        try:
            discount_value = float(data.get("discount_value"))
            if discount_value <= 0:
                raise ValueError
            normalized["discount_value"] = discount_value
        except (TypeError, ValueError):
            errors["discount_value"] = "discount_value must be a positive number."

    if "minimum_order_amount" in provided_fields:
        try:
            minimum_order_amount = float(data.get("minimum_order_amount"))
            if minimum_order_amount < 0:
                raise ValueError
            normalized["minimum_order_amount"] = minimum_order_amount
        except (TypeError, ValueError):
            errors["minimum_order_amount"] = "minimum_order_amount must be a non-negative number."

    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    if errors:
        return {"errors": errors}
    return normalized
