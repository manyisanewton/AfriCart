def validate_vendor_product_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    required_fields = ["name", "slug", "sku", "category_id", "brand_id", "price", "stock_quantity"]
    for field in required_fields:
        if data.get(field) in (None, ""):
            errors[field] = f"{field} is required."

    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["category_id"] = "category_id must be a positive integer."

    try:
        brand_id = int(data.get("brand_id"))
        if brand_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["brand_id"] = "brand_id must be a positive integer."

    try:
        price = float(data.get("price"))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["price"] = "price must be a non-negative number."

    try:
        stock_quantity = int(data.get("stock_quantity"))
        if stock_quantity < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["stock_quantity"] = "stock_quantity must be a non-negative integer."

    if errors:
        return {"errors": errors}

    return {
        "name": str(data["name"]).strip(),
        "slug": str(data["slug"]).strip(),
        "sku": str(data["sku"]).strip(),
        "category_id": category_id,
        "brand_id": brand_id,
        "price": price,
        "stock_quantity": stock_quantity,
        "short_description": str(data.get("short_description") or "").strip() or None,
        "description": str(data.get("description") or "").strip() or None,
        "is_active": bool(data.get("is_active", True)),
        "is_featured": bool(data.get("is_featured", False)),
    }


def validate_stock_payload(payload: dict | None) -> dict:
    data = payload or {}
    try:
        stock_quantity = int(data.get("stock_quantity"))
        if stock_quantity < 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"stock_quantity": "stock_quantity must be a non-negative integer."}}

    return {"stock_quantity": stock_quantity}


def validate_vendor_kyc_payload(payload: dict | None) -> dict:
    data = payload or {}
    required_fields = [
        "legal_business_name",
        "registration_number",
        "contact_person_name",
        "contact_person_id_number",
        "document_url",
    ]
    errors = {}

    for field in required_fields:
        value = str(data.get(field, "")).strip()
        if not value:
            errors[field] = f"{field} is required."

    if errors:
        return {"errors": errors}

    return {
        "legal_business_name": str(data["legal_business_name"]).strip(),
        "registration_number": str(data["registration_number"]).strip(),
        "tax_id": str(data.get("tax_id") or "").strip() or None,
        "contact_person_name": str(data["contact_person_name"]).strip(),
        "contact_person_id_number": str(data["contact_person_id_number"]).strip(),
        "document_url": str(data["document_url"]).strip(),
    }


def serialize_vendor_kyc_submission(submission) -> dict:
    return {
        "id": submission.id,
        "vendor_id": submission.vendor_id,
        "legal_business_name": submission.legal_business_name,
        "registration_number": submission.registration_number,
        "tax_id": submission.tax_id,
        "contact_person_name": submission.contact_person_name,
        "contact_person_id_number": submission.contact_person_id_number,
        "document_url": submission.document_url,
        "status": submission.status.value,
        "admin_note": submission.admin_note,
        "submitted_at": submission.submitted_at.isoformat(),
        "reviewed_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        "updated_at": submission.updated_at.isoformat(),
    }
