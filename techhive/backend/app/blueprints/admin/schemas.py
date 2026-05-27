import re
from datetime import datetime

from app.models import (
    OrderStatus,
    RefundStatus,
    SupplierStatus,
    SupportTicketStatus,
    UserRole,
    VendorKYCStatus,
    VendorStatus,
)


def _slugify_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return normalized.strip("-")


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


def validate_stock_alert_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {"open", "closed"}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be either 'open' or 'closed'."}}
    return {"status": status}


def validate_supplier_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {
        "status",
        "company_name",
        "contact_name",
        "phone",
        "country_code",
        "website",
        "notes",
    }
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"supplier": "At least one supplier field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    errors = {}

    if "status" in provided_fields:
        status = str(data.get("status", "")).strip().lower()
        allowed_statuses = {status.value for status in SupplierStatus}
        if status not in allowed_statuses:
            errors["status"] = "status must be a supported supplier status."
        else:
            normalized["status"] = status

    if "company_name" in provided_fields:
        company_name = str(data.get("company_name", "")).strip()
        if not company_name:
            errors["company_name"] = "company_name cannot be blank."
        else:
            normalized["company_name"] = company_name

    if "contact_name" in provided_fields:
        normalized["contact_name"] = str(data.get("contact_name") or "").strip() or None

    if "phone" in provided_fields:
        normalized["phone"] = str(data.get("phone") or "").strip() or None

    if "country_code" in provided_fields:
        normalized["country_code"] = str(data.get("country_code") or "").strip().upper() or None

    if "website" in provided_fields:
        normalized["website"] = str(data.get("website") or "").strip() or None

    if "notes" in provided_fields:
        normalized["notes"] = str(data.get("notes") or "").strip() or None

    if errors:
        return {"errors": errors}
    return normalized


def validate_supplier_create_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    try:
        user_id = int(data.get("user_id"))
        if user_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["user_id"] = "user_id must be a positive integer."
        user_id = None

    partner_id = data.get("partner_id")
    normalized_partner_id = None
    if partner_id not in (None, "", 0):
        try:
            normalized_partner_id = int(partner_id)
            if normalized_partner_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["partner_id"] = "partner_id must be a positive integer."

    company_name = str(data.get("company_name", "")).strip()
    if not company_name:
        errors["company_name"] = "company_name is required."

    status = str(data.get("status", "pending")).strip().lower()
    allowed_statuses = {status.value for status in SupplierStatus}
    if status not in allowed_statuses:
        errors["status"] = "status must be a supported supplier status."

    if errors:
        return {"errors": errors}

    return {
        "user_id": user_id,
        "partner_id": normalized_partner_id,
        "company_name": company_name,
        "contact_name": str(data.get("contact_name") or "").strip() or None,
        "phone": str(data.get("phone") or "").strip() or None,
        "country_code": str(data.get("country_code") or "").strip().upper() or None,
        "website": str(data.get("website") or "").strip() or None,
        "notes": str(data.get("notes") or "").strip() or None,
        "status": status,
    }


def _coerce_optional_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def validate_offer_component_payload(payload: dict | None, *, kind: str) -> dict:
    data = payload or {}
    errors = {}

    component_type = str(data.get("type", "")).strip()
    if not component_type:
        errors["type"] = f"{kind} type is required."

    range_id = data.get("range_id")
    normalized_range_id = None
    if range_id not in (None, "", 0):
        try:
            normalized_range_id = int(range_id)
            if normalized_range_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["range_id"] = "range_id must be a positive integer."

    normalized_max_affected_items = None
    if kind == "benefit":
        raw_max_affected_items = data.get("max_affected_items")
        if raw_max_affected_items not in (None, ""):
            try:
                normalized_max_affected_items = int(raw_max_affected_items)
                if normalized_max_affected_items <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors["max_affected_items"] = "max_affected_items must be a positive integer."

    if errors:
        return {"errors": errors}

    normalized = {
        "type": component_type,
        "range_id": normalized_range_id,
        "value": str(data.get("value") or "").strip() or None,
        "proxy_class": str(data.get("proxy_class") or "").strip() or None,
    }
    if kind == "benefit":
        normalized["max_affected_items"] = normalized_max_affected_items
    return normalized


def validate_offer_component_update_payload(payload: dict | None, *, kind: str) -> dict:
    data = payload or {}
    allowed_fields = {"type", "range_id", "value", "proxy_class"}
    if kind == "benefit":
        allowed_fields.add("max_affected_items")
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {kind: f"At least one {kind} field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    errors = {}

    if "type" in provided_fields:
        component_type = str(data.get("type", "")).strip()
        if not component_type:
            errors["type"] = "type cannot be blank."
        else:
            normalized["type"] = component_type

    if "range_id" in provided_fields:
        range_id = data.get("range_id")
        if range_id in (None, "", 0):
            normalized["range_id"] = None
        else:
            try:
                normalized_range_id = int(range_id)
                if normalized_range_id <= 0:
                    raise ValueError
                normalized["range_id"] = normalized_range_id
            except (TypeError, ValueError):
                errors["range_id"] = "range_id must be a positive integer."

    if "value" in provided_fields:
        normalized["value"] = str(data.get("value") or "").strip() or None

    if "proxy_class" in provided_fields:
        normalized["proxy_class"] = str(data.get("proxy_class") or "").strip() or None

    if kind == "benefit" and "max_affected_items" in provided_fields:
        raw = data.get("max_affected_items")
        if raw in (None, ""):
            normalized["max_affected_items"] = None
        else:
            try:
                max_affected_items = int(raw)
                if max_affected_items <= 0:
                    raise ValueError
                normalized["max_affected_items"] = max_affected_items
            except (TypeError, ValueError):
                errors["max_affected_items"] = "max_affected_items must be a positive integer."

    if errors:
        return {"errors": errors}
    return normalized


def validate_offer_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    slug = str(data.get("slug", "")).strip() or _slugify_text(name)
    if not slug:
        errors["slug"] = "slug is required."

    offer_type = str(data.get("offer_type", "")).strip()
    if not offer_type:
        errors["offer_type"] = "offer_type is required."

    status = str(data.get("status", "")).strip()
    if not status:
        errors["status"] = "status is required."

    try:
        condition_id = int(data.get("condition_id"))
        if condition_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["condition_id"] = "condition_id must be a positive integer."
        condition_id = None

    try:
        benefit_id = int(data.get("benefit_id"))
        if benefit_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["benefit_id"] = "benefit_id must be a positive integer."
        benefit_id = None

    try:
        priority = int(data.get("priority", 0))
    except (TypeError, ValueError):
        errors["priority"] = "priority must be an integer."
        priority = 0

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "slug": slug,
        "description": str(data.get("description") or "").strip() or None,
        "offer_type": offer_type,
        "exclusive": bool(data.get("exclusive", False)),
        "status": status,
        "priority": priority,
        "start_datetime": _coerce_optional_datetime(data.get("start_datetime")),
        "end_datetime": _coerce_optional_datetime(data.get("end_datetime")),
        "condition_id": condition_id,
        "benefit_id": benefit_id,
    }


def validate_offer_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {
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
    }
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"offer": "At least one offer field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    errors = {}

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

    if "offer_type" in provided_fields:
        offer_type = str(data.get("offer_type", "")).strip()
        if not offer_type:
            errors["offer_type"] = "offer_type cannot be blank."
        else:
            normalized["offer_type"] = offer_type

    if "exclusive" in provided_fields:
        normalized["exclusive"] = bool(data.get("exclusive"))

    if "status" in provided_fields:
        status = str(data.get("status", "")).strip()
        if not status:
            errors["status"] = "status cannot be blank."
        else:
            normalized["status"] = status

    if "priority" in provided_fields:
        try:
            normalized["priority"] = int(data.get("priority", 0))
        except (TypeError, ValueError):
            errors["priority"] = "priority must be an integer."

    if "start_datetime" in provided_fields:
        normalized["start_datetime"] = _coerce_optional_datetime(data.get("start_datetime"))

    if "end_datetime" in provided_fields:
        normalized["end_datetime"] = _coerce_optional_datetime(data.get("end_datetime"))

    if "condition_id" in provided_fields:
        try:
            condition_id = int(data.get("condition_id"))
            if condition_id <= 0:
                raise ValueError
            normalized["condition_id"] = condition_id
        except (TypeError, ValueError):
            errors["condition_id"] = "condition_id must be a positive integer."

    if "benefit_id" in provided_fields:
        try:
            benefit_id = int(data.get("benefit_id"))
            if benefit_id <= 0:
                raise ValueError
            normalized["benefit_id"] = benefit_id
        except (TypeError, ValueError):
            errors["benefit_id"] = "benefit_id must be a positive integer."

    if errors:
        return {"errors": errors}
    return normalized


def validate_offer_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip()
    if not status:
        return {"errors": {"status": "status is required."}}
    return {"status": status}


def validate_voucher_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    code = str(data.get("code", "")).strip().upper()
    if not code:
        errors["code"] = "code is required."

    usage = str(data.get("usage", "")).strip()
    if not usage:
        errors["usage"] = "usage is required."

    start_datetime = _coerce_optional_datetime(data.get("start_datetime"))
    end_datetime = _coerce_optional_datetime(data.get("end_datetime"))
    if start_datetime is None:
        errors["start_datetime"] = "start_datetime is required and must be a valid datetime."
    if end_datetime is None:
        errors["end_datetime"] = "end_datetime is required and must be a valid datetime."
    if start_datetime and end_datetime and start_datetime >= end_datetime:
        errors["end_datetime"] = "end_datetime must be after start_datetime."

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "code": code,
        "usage": usage,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
    }


def validate_voucher_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "code", "usage", "start_datetime", "end_datetime"}
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"voucher": "At least one voucher field must be provided."}}

    errors = {}
    normalized = {"provided_fields": provided_fields}

    if "name" in provided_fields:
        name = str(data.get("name", "")).strip()
        if not name:
            errors["name"] = "name cannot be blank."
        else:
            normalized["name"] = name

    if "code" in provided_fields:
        code = str(data.get("code", "")).strip().upper()
        if not code:
            errors["code"] = "code cannot be blank."
        else:
            normalized["code"] = code

    if "usage" in provided_fields:
        usage = str(data.get("usage", "")).strip()
        if not usage:
            errors["usage"] = "usage cannot be blank."
        else:
            normalized["usage"] = usage

    if "start_datetime" in provided_fields:
        start_datetime = _coerce_optional_datetime(data.get("start_datetime"))
        if start_datetime is None:
            errors["start_datetime"] = "start_datetime must be a valid datetime."
        else:
            normalized["start_datetime"] = start_datetime

    if "end_datetime" in provided_fields:
        end_datetime = _coerce_optional_datetime(data.get("end_datetime"))
        if end_datetime is None:
            errors["end_datetime"] = "end_datetime must be a valid datetime."
        else:
            normalized["end_datetime"] = end_datetime

    start_datetime = normalized.get("start_datetime")
    end_datetime = normalized.get("end_datetime")
    if start_datetime and end_datetime and start_datetime >= end_datetime:
        errors["end_datetime"] = "end_datetime must be after start_datetime."

    if errors:
        return {"errors": errors}
    return normalized


def validate_voucher_offer_payload(payload: dict | None) -> dict:
    data = payload or {}
    try:
        offer_id = int(data.get("offer_id"))
        if offer_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"offer_id": "offer_id must be a positive integer."}}
    return {"offer_id": offer_id}


def validate_range_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    slug = str(data.get("slug", "")).strip() or _slugify_text(name)
    if not slug:
        errors["slug"] = "slug is required."

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "slug": slug,
        "description": str(data.get("description") or "").strip() or None,
        "is_public": bool(data.get("is_public", True)),
        "includes_all_products": bool(data.get("includes_all_products", False)),
    }


def validate_range_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "slug", "description", "is_public", "includes_all_products"}
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"range": "At least one range field must be provided."}}

    errors = {}
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
    if "is_public" in provided_fields:
        normalized["is_public"] = bool(data.get("is_public"))
    if "includes_all_products" in provided_fields:
        normalized["includes_all_products"] = bool(data.get("includes_all_products"))

    if errors:
        return {"errors": errors}
    return normalized


def validate_range_product_payload(payload: dict | None) -> dict:
    data = payload or {}
    try:
        product_id = int(data.get("product_id"))
        if product_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"product_id": "product_id must be a positive integer."}}
    return {"product_id": product_id}


def validate_admin_review_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"status", "title", "body", "score"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}

    if not provided_fields:
        return {"errors": {"review": "At least one review field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "status" in provided_fields:
        try:
            status = int(data.get("status"))
            if status not in {0, 1, 2}:
                raise ValueError
            normalized["status"] = status
        except (TypeError, ValueError):
            errors["status"] = "status must be 0, 1, or 2."

    if "title" in provided_fields:
        normalized["title"] = str(data.get("title") or "").strip() or None

    if "body" in provided_fields:
        body = str(data.get("body", "")).strip()
        if not body:
            errors["body"] = "body cannot be blank."
        else:
            normalized["body"] = body

    if "score" in provided_fields:
        try:
            score = int(data.get("score"))
            if score < 1 or score > 5:
                raise ValueError
            normalized["score"] = score
        except (TypeError, ValueError):
            errors["score"] = "score must be an integer between 1 and 5."

    if errors:
        return {"errors": errors}
    return normalized


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
    parent_id = data.get("parent_id")
    if not name:
        return {"errors": {"name": "name is required."}}
    if not slug:
        return {"errors": {"slug": "slug is required."}}
    normalized_parent_id = None
    if parent_id not in (None, ""):
        try:
            normalized_parent_id = int(parent_id)
            if normalized_parent_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return {"errors": {"parent_id": "parent_id must be a positive integer."}}
    return {
        "name": name,
        "slug": slug,
        "description": str(data.get("description") or "").strip() or None,
        "website_url": str(data.get("website_url") or "").strip() or None,
        "logo_url": str(data.get("logo_url") or "").strip() or None,
        "parent_id": normalized_parent_id,
    }


def validate_named_entity_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "slug", "description", "website_url", "logo_url", "is_active", "parent_id"}
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

    if "parent_id" in provided_fields:
        parent_id = data.get("parent_id")
        if parent_id in (None, ""):
            normalized["parent_id"] = None
        else:
            try:
                normalized["parent_id"] = int(parent_id)
                if normalized["parent_id"] <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors["parent_id"] = "parent_id must be a positive integer or null."

    if errors:
        return {"errors": errors}
    return normalized


def validate_delivery_zone_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    city = str(data.get("city", "")).strip()
    if not name:
        errors["name"] = "name is required."
    if not city:
        errors["city"] = "city is required."

    try:
        fee = float(data.get("fee"))
        if fee < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["fee"] = "fee must be a non-negative number."
        fee = None

    try:
        estimated_days_min = int(data.get("estimated_days_min"))
        if estimated_days_min <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["estimated_days_min"] = "estimated_days_min must be a positive integer."
        estimated_days_min = None

    try:
        estimated_days_max = int(data.get("estimated_days_max"))
        if estimated_days_max <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["estimated_days_max"] = "estimated_days_max must be a positive integer."
        estimated_days_max = None

    if (
        estimated_days_min is not None
        and estimated_days_max is not None
        and estimated_days_max < estimated_days_min
    ):
        errors["estimated_days_max"] = "estimated_days_max must be greater than or equal to estimated_days_min."

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "city": city,
        "fee": fee,
        "estimated_days_min": estimated_days_min,
        "estimated_days_max": estimated_days_max,
        "is_active": bool(data.get("is_active", True)),
    }


def validate_delivery_zone_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "city", "fee", "estimated_days_min", "estimated_days_max", "is_active"}
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

    if "city" in provided_fields:
        city = str(data.get("city", "")).strip()
        if not city:
            errors["city"] = "city cannot be blank."
        else:
            normalized["city"] = city

    if "fee" in provided_fields:
        try:
            fee = float(data.get("fee"))
            if fee < 0:
                raise ValueError
            normalized["fee"] = fee
        except (TypeError, ValueError):
            errors["fee"] = "fee must be a non-negative number."

    if "estimated_days_min" in provided_fields:
        try:
            estimated_days_min = int(data.get("estimated_days_min"))
            if estimated_days_min <= 0:
                raise ValueError
            normalized["estimated_days_min"] = estimated_days_min
        except (TypeError, ValueError):
            errors["estimated_days_min"] = "estimated_days_min must be a positive integer."

    if "estimated_days_max" in provided_fields:
        try:
            estimated_days_max = int(data.get("estimated_days_max"))
            if estimated_days_max <= 0:
                raise ValueError
            normalized["estimated_days_max"] = estimated_days_max
        except (TypeError, ValueError):
            errors["estimated_days_max"] = "estimated_days_max must be a positive integer."

    min_days = normalized.get("estimated_days_min")
    max_days = normalized.get("estimated_days_max")
    if min_days is not None and max_days is not None and max_days < min_days:
        errors["estimated_days_max"] = "estimated_days_max must be greater than or equal to estimated_days_min."

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


def validate_product_type_payload(payload: dict | None) -> dict:
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
        "requires_shipping": bool(data.get("requires_shipping", True)),
        "track_stock": bool(data.get("track_stock", True)),
        "is_active": bool(data.get("is_active", True)),
    }


def validate_product_type_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "slug", "requires_shipping", "track_stock", "is_active"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}

    if not provided_fields:
        return {"errors": {"product_type": "At least one field must be provided."}}

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

    if "requires_shipping" in provided_fields:
        normalized["requires_shipping"] = bool(data.get("requires_shipping"))

    if "track_stock" in provided_fields:
        normalized["track_stock"] = bool(data.get("track_stock"))

    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    if errors:
        return {"errors": errors}
    return normalized


def validate_product_attribute_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    try:
        product_type_id = int(data.get("product_type_id", data.get("product_class_id")))
        if product_type_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["product_type_id"] = "product_type_id must be a positive integer."
        product_type_id = None

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    code = str(data.get("code", "")).strip()
    if not code:
        errors["code"] = "code is required."

    attribute_type = str(data.get("type", "")).strip().lower() or "text"
    allowed_types = {
        "text",
        "integer",
        "boolean",
        "float",
        "richtext",
        "date",
        "datetime",
        "option",
        "multi_option",
        "file",
        "image",
    }
    if attribute_type not in allowed_types:
        errors["type"] = "type must be a supported attribute type."

    if errors:
        return {"errors": errors}

    return {
        "product_type_id": product_type_id,
        "name": name,
        "code": code,
        "type": attribute_type,
        "required": bool(data.get("required", False)),
        "option_group_id": data.get("option_group_id"),
    }


def validate_product_attribute_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "code", "type", "required", "option_group_id"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}

    if not provided_fields:
        return {"errors": {"attribute": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "name" in provided_fields:
        name = str(data.get("name", "")).strip()
        if not name:
            errors["name"] = "name cannot be blank."
        else:
            normalized["name"] = name

    if "code" in provided_fields:
        code = str(data.get("code", "")).strip()
        if not code:
            errors["code"] = "code cannot be blank."
        else:
            normalized["code"] = code

    if "type" in provided_fields:
        attribute_type = str(data.get("type", "")).strip().lower()
        allowed_types = {
            "text",
            "integer",
            "boolean",
            "float",
            "richtext",
            "date",
            "datetime",
            "option",
            "multi_option",
            "file",
            "image",
        }
        if attribute_type not in allowed_types:
            errors["type"] = "type must be a supported attribute type."
        else:
            normalized["type"] = attribute_type

    if "required" in provided_fields:
        normalized["required"] = bool(data.get("required"))

    if "option_group_id" in provided_fields:
        normalized["option_group_id"] = data.get("option_group_id")

    if errors:
        return {"errors": errors}
    return normalized


def validate_product_option_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    code = str(data.get("code", "")).strip()
    if not code:
        errors["code"] = "code is required."

    option_type = str(data.get("type", "")).strip().lower() or "text"
    allowed_types = {
        "text",
        "integer",
        "boolean",
        "float",
        "richtext",
        "date",
        "datetime",
        "option",
        "multi_option",
        "file",
        "image",
    }
    if option_type not in allowed_types:
        errors["type"] = "type must be a supported option type."

    try:
        sort_order = int(data.get("order", data.get("sort_order", 0)))
        if sort_order < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["order"] = "order must be a non-negative integer."
        sort_order = 0

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "code": code,
        "type": option_type,
        "required": bool(data.get("required", False)),
        "help_text": str(data.get("help_text", "") or "").strip(),
        "sort_order": sort_order,
    }


def validate_product_option_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "code", "type", "required", "help_text", "order", "sort_order"}
    provided_fields = {field for field in allowed_fields if field in data}
    errors = {}

    if not provided_fields:
        return {"errors": {"option": "At least one field must be provided."}}

    normalized = {"provided_fields": provided_fields}

    if "name" in provided_fields:
        name = str(data.get("name", "")).strip()
        if not name:
            errors["name"] = "name cannot be blank."
        else:
            normalized["name"] = name

    if "code" in provided_fields:
        code = str(data.get("code", "")).strip()
        if not code:
            errors["code"] = "code cannot be blank."
        else:
            normalized["code"] = code

    if "type" in provided_fields:
        option_type = str(data.get("type", "")).strip().lower()
        allowed_types = {
            "text",
            "integer",
            "boolean",
            "float",
            "richtext",
            "date",
            "datetime",
            "option",
            "multi_option",
            "file",
            "image",
        }
        if option_type not in allowed_types:
            errors["type"] = "type must be a supported option type."
        else:
            normalized["type"] = option_type

    if "required" in provided_fields:
        normalized["required"] = bool(data.get("required"))

    if "help_text" in provided_fields:
        normalized["help_text"] = str(data.get("help_text", "") or "").strip()

    if "order" in provided_fields or "sort_order" in provided_fields:
        try:
            sort_order = int(data.get("order", data.get("sort_order", 0)))
            if sort_order < 0:
                raise ValueError
            normalized["sort_order"] = sort_order
        except (TypeError, ValueError):
            errors["order"] = "order must be a non-negative integer."

    if errors:
        return {"errors": errors}
    return normalized


def validate_admin_product_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "name is required."

    try:
        vendor_id = int(data.get("vendor_id"))
        if vendor_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["vendor_id"] = "vendor_id must be a positive integer."
        vendor_id = None

    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["category_id"] = "category_id must be a positive integer."
        category_id = None

    try:
        brand_id = int(data.get("brand_id"))
        if brand_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["brand_id"] = "brand_id must be a positive integer."
        brand_id = None

    try:
        price = float(data.get("price"))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["price"] = "price must be a non-negative number."
        price = None

    try:
        stock_quantity = int(data.get("stock_quantity"))
        if stock_quantity < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["stock_quantity"] = "stock_quantity must be a non-negative integer."
        stock_quantity = None

    try:
        low_stock_threshold = int(data.get("low_stock_threshold", 5))
        if low_stock_threshold < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["low_stock_threshold"] = "low_stock_threshold must be a non-negative integer."
        low_stock_threshold = 5

    compare_at_price = None
    if data.get("compare_at_price") not in (None, ""):
        try:
            compare_at_price = float(data.get("compare_at_price"))
            if compare_at_price < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["compare_at_price"] = "compare_at_price must be a non-negative number."

    slug = str(data.get("slug") or "").strip() or _slugify_text(name)
    if not slug:
        errors["slug"] = "slug is required."

    sku = str(data.get("sku") or "").strip() or slug.upper().replace("-", "-")
    if not sku:
        errors["sku"] = "sku is required."

    currency = str(data.get("currency") or "KES").strip().upper() or "KES"
    if len(currency) != 3:
        errors["currency"] = "currency must be a 3-letter code."

    if errors:
        return {"errors": errors}

    return {
        "vendor_id": vendor_id,
        "category_id": category_id,
        "brand_id": brand_id,
        "name": name,
        "slug": slug,
        "sku": sku,
        "price": price,
        "compare_at_price": compare_at_price,
        "currency": currency,
        "stock_quantity": stock_quantity,
        "low_stock_threshold": low_stock_threshold,
        "short_description": str(data.get("short_description") or "").strip() or None,
        "description": str(data.get("description") or "").strip() or None,
        "is_active": bool(data.get("is_active", True)),
        "is_featured": bool(data.get("is_featured", False)),
    }


def validate_admin_product_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    field_names = {
        "vendor_id",
        "category_id",
        "brand_id",
        "name",
        "slug",
        "sku",
        "price",
        "compare_at_price",
        "currency",
        "stock_quantity",
        "low_stock_threshold",
        "short_description",
        "description",
        "is_active",
        "is_featured",
    }
    provided_fields = {field for field in field_names if field in data}
    if not provided_fields:
        return {"errors": {"product": "At least one product field must be provided."}}

    errors = {}
    normalized = {"provided_fields": provided_fields}

    if "vendor_id" in provided_fields:
        try:
            vendor_id = int(data.get("vendor_id"))
            if vendor_id <= 0:
                raise ValueError
            normalized["vendor_id"] = vendor_id
        except (TypeError, ValueError):
            errors["vendor_id"] = "vendor_id must be a positive integer."

    if "category_id" in provided_fields:
        try:
            category_id = int(data.get("category_id"))
            if category_id <= 0:
                raise ValueError
            normalized["category_id"] = category_id
        except (TypeError, ValueError):
            errors["category_id"] = "category_id must be a positive integer."

    if "brand_id" in provided_fields:
        try:
            brand_id = int(data.get("brand_id"))
            if brand_id <= 0:
                raise ValueError
            normalized["brand_id"] = brand_id
        except (TypeError, ValueError):
            errors["brand_id"] = "brand_id must be a positive integer."

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

    if "sku" in provided_fields:
        sku = str(data.get("sku", "")).strip()
        if not sku:
            errors["sku"] = "sku cannot be blank."
        else:
            normalized["sku"] = sku

    if "price" in provided_fields:
        try:
            price = float(data.get("price"))
            if price < 0:
                raise ValueError
            normalized["price"] = price
        except (TypeError, ValueError):
            errors["price"] = "price must be a non-negative number."

    if "compare_at_price" in provided_fields:
        raw_value = data.get("compare_at_price")
        if raw_value in (None, ""):
            normalized["compare_at_price"] = None
        else:
            try:
                compare_at_price = float(raw_value)
                if compare_at_price < 0:
                    raise ValueError
                normalized["compare_at_price"] = compare_at_price
            except (TypeError, ValueError):
                errors["compare_at_price"] = "compare_at_price must be a non-negative number."

    if "currency" in provided_fields:
        currency = str(data.get("currency") or "").strip().upper()
        if len(currency) != 3:
            errors["currency"] = "currency must be a 3-letter code."
        else:
            normalized["currency"] = currency

    if "stock_quantity" in provided_fields:
        try:
            stock_quantity = int(data.get("stock_quantity"))
            if stock_quantity < 0:
                raise ValueError
            normalized["stock_quantity"] = stock_quantity
        except (TypeError, ValueError):
            errors["stock_quantity"] = "stock_quantity must be a non-negative integer."

    if "low_stock_threshold" in provided_fields:
        try:
            low_stock_threshold = int(data.get("low_stock_threshold"))
            if low_stock_threshold < 0:
                raise ValueError
            normalized["low_stock_threshold"] = low_stock_threshold
        except (TypeError, ValueError):
            errors["low_stock_threshold"] = "low_stock_threshold must be a non-negative integer."

    if "short_description" in provided_fields:
        normalized["short_description"] = str(data.get("short_description") or "").strip() or None

    if "description" in provided_fields:
        normalized["description"] = str(data.get("description") or "").strip() or None

    if "is_active" in provided_fields:
        normalized["is_active"] = bool(data.get("is_active"))

    if "is_featured" in provided_fields:
        normalized["is_featured"] = bool(data.get("is_featured"))

    if errors:
        return {"errors": errors}
    return normalized


def validate_user_active_payload(payload: dict | None) -> dict:
    data = payload or {}
    if "is_active" not in data:
        return {"errors": {"is_active": "is_active is required."}}
    return {"is_active": bool(data.get("is_active"))}


def validate_partner_payload(payload: dict | None) -> dict:
    data = payload or {}
    name = str(data.get("name", "")).strip()
    code = str(data.get("code") or "").strip() or None

    if not name:
        return {"errors": {"name": "name is required."}}

    return {
        "name": name,
        "code": code,
    }


def validate_partner_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"name", "code"}
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"partner": "At least one partner field must be provided."}}

    normalized = {"provided_fields": provided_fields}
    errors = {}

    if "name" in provided_fields:
        name = str(data.get("name", "")).strip()
        if not name:
            errors["name"] = "name cannot be blank."
        else:
            normalized["name"] = name

    if "code" in provided_fields:
        normalized["code"] = str(data.get("code") or "").strip() or None

    if errors:
        return {"errors": errors}
    return normalized


def validate_admin_user_create_payload(payload: dict | None) -> dict:
    data = payload or {}
    required_fields = {"email", "first_name", "last_name", "role"}
    errors = {}

    for field in required_fields:
        if not str(data.get(field, "")).strip():
            errors[field] = f"{field} is required."

    email = str(data.get("email", "")).strip().lower()
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors["email"] = "email must be a valid email address."

    role = str(data.get("role", "")).strip().lower()
    allowed_roles = {role.value for role in UserRole}
    if role and role not in allowed_roles:
        errors["role"] = "role must be a supported user role."

    if errors:
        return {"errors": errors}

    return {
        "email": email,
        "first_name": str(data.get("first_name", "")).strip(),
        "last_name": str(data.get("last_name", "")).strip(),
        "phone_number": str(data.get("phone_number") or "").strip() or None,
        "role": role,
        "is_active": bool(data.get("is_active", True)),
        "email_verified": bool(data.get("email_verified", False)),
    }


def validate_order_status_payload(payload: dict | None) -> dict:
    data = payload or {}
    status = str(data.get("status", "")).strip().lower()
    allowed_statuses = {status.value for status in OrderStatus}
    if status not in allowed_statuses:
        return {"errors": {"status": "status must be a supported order status."}}
    return {"status": status}


def validate_admin_order_update_payload(payload: dict | None) -> dict:
    data = payload or {}
    allowed_fields = {"status", "delivery_status", "tracking_token", "notes", "delivery_agent_id"}
    provided_fields = {field for field in allowed_fields if field in data}
    if not provided_fields:
        return {"errors": {"order": "At least one order field must be provided."}}

    errors = {}
    normalized = {"provided_fields": provided_fields}

    if "status" in provided_fields:
        status = str(data.get("status", "")).strip().lower()
        allowed_statuses = {status.value for status in OrderStatus}
        if status not in allowed_statuses:
            errors["status"] = "status must be a supported order status."
        else:
            normalized["status"] = status

    if "delivery_status" in provided_fields:
        delivery_status = str(data.get("delivery_status", "")).strip().lower()
        allowed_delivery_statuses = {"processing", "assigned", "in_transit", "delivered", "failed_attempt"}
        if delivery_status not in allowed_delivery_statuses:
            errors["delivery_status"] = "delivery_status must be one of processing, assigned, in_transit, delivered, or failed_attempt."
        else:
            normalized["delivery_status"] = delivery_status

    if "tracking_token" in provided_fields:
        tracking_token = str(data.get("tracking_token", "")).strip()
        if not tracking_token:
            errors["tracking_token"] = "tracking_token cannot be blank."
        else:
            normalized["tracking_token"] = tracking_token

    if "notes" in provided_fields:
        normalized["notes"] = str(data.get("notes") or "").strip() or None

    if "delivery_agent_id" in provided_fields:
        raw_agent_id = data.get("delivery_agent_id")
        if raw_agent_id in (None, "", 0):
            normalized["delivery_agent_id"] = None
        else:
            try:
                delivery_agent_id = int(raw_agent_id)
                if delivery_agent_id <= 0:
                    raise ValueError
                normalized["delivery_agent_id"] = delivery_agent_id
            except (TypeError, ValueError):
                errors["delivery_agent_id"] = "delivery_agent_id must be a positive integer."

    if errors:
        return {"errors": errors}
    return normalized


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
