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
