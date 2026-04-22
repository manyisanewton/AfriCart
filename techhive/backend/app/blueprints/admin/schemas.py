from app.models import OrderStatus, UserRole, VendorStatus


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
