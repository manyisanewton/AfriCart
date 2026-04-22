def validate_cart_item_payload(payload: dict | None) -> dict:
    data = payload or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    errors = {}

    try:
        product_id = int(product_id)
        if product_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["product_id"] = "product_id must be a positive integer."

    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors["quantity"] = "quantity must be a positive integer."

    if errors:
        return {"errors": errors}

    return {"product_id": product_id, "quantity": quantity}


def validate_quantity_payload(payload: dict | None) -> dict:
    data = payload or {}
    quantity = data.get("quantity")

    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"quantity": "quantity must be a positive integer."}}

    return {"quantity": quantity}


def validate_product_id_payload(payload: dict | None) -> dict:
    data = payload or {}
    product_id = data.get("product_id")

    try:
        product_id = int(product_id)
        if product_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"product_id": "product_id must be a positive integer."}}

    return {"product_id": product_id}
