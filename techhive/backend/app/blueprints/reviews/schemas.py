def validate_review_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    try:
        product_id = int(data.get("product_id"))
        if product_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["product_id"] = "product_id must be a positive integer."

    try:
        rating = int(data.get("rating"))
        if rating < 1 or rating > 5:
            raise ValueError
    except (TypeError, ValueError):
        errors["rating"] = "rating must be an integer between 1 and 5."

    comment = str(data.get("comment", "")).strip()
    if not comment:
        errors["comment"] = "comment is required."

    if errors:
        return {"errors": errors}

    title = str(data.get("title") or "").strip() or None
    return {
        "product_id": product_id,
        "rating": rating,
        "title": title,
        "comment": comment,
    }
