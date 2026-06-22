from app.utils.api import parse_positive_int


def _validate_delivery_location(payload: dict | None) -> tuple[dict | None, dict[str, str]]:
    data = payload if isinstance(payload, dict) else None
    if data is None:
        return None, {}

    errors = {}
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude in (None, "") or longitude in (None, ""):
        return None, {}

    try:
        normalized_latitude = float(latitude)
        if normalized_latitude < -90 or normalized_latitude > 90:
            raise ValueError
    except (TypeError, ValueError):
        errors["delivery_location.latitude"] = "delivery_location.latitude must be between -90 and 90."
        normalized_latitude = None

    try:
        normalized_longitude = float(longitude)
        if normalized_longitude < -180 or normalized_longitude > 180:
            raise ValueError
    except (TypeError, ValueError):
        errors["delivery_location.longitude"] = "delivery_location.longitude must be between -180 and 180."
        normalized_longitude = None

    if errors:
        return None, errors

    return {
        "latitude": normalized_latitude,
        "longitude": normalized_longitude,
        "label": str(data.get("label") or "").strip() or None,
    }, {}


def validate_checkout_order_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    address = data.get("address") if isinstance(data.get("address"), dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else None

    email = str(customer.get("email") or "").strip().lower()
    if not email:
        errors["customer.email"] = "customer.email is required."

    recipient_name = str(address.get("recipient_name") or customer.get("name") or "").strip()
    if not recipient_name:
        errors["address.recipient_name"] = "address.recipient_name is required."

    phone_number = str(address.get("phone_number") or customer.get("phone_number") or "").strip()
    if not phone_number:
        errors["address.phone_number"] = "address.phone_number is required."

    address_line_1 = str(address.get("address_line_1") or "").strip()
    if not address_line_1:
        errors["address.address_line_1"] = "address.address_line_1 is required."

    city = str(address.get("city") or "").strip()
    if not city:
        errors["address.city"] = "address.city is required."

    if not items:
        errors["items"] = "At least one cart item is required."

    normalized_items = []
    if isinstance(items, list):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors[f"items[{index}]"] = "Each item must be an object."
                continue

            product_id, product_error = parse_positive_int(item.get("product_id"), field_name=f"items[{index}].product_id")
            quantity, quantity_error = parse_positive_int(item.get("quantity"), field_name=f"items[{index}].quantity")

            if product_error:
                errors.update(product_error)
            if quantity_error:
                errors.update(quantity_error)
            if product_error or quantity_error:
                continue

            normalized_items.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                }
            )

    delivery_location, location_errors = _validate_delivery_location(data.get("delivery_location"))
    errors.update(location_errors)

    if errors:
        return {"errors": errors}

    return {
        "customer": {
            "email": email,
            "name": str(customer.get("name") or recipient_name).strip(),
            "phone_number": str(customer.get("phone_number") or phone_number).strip() or None,
        },
        "address": {
            "label": str(address.get("label") or "Checkout").strip() or "Checkout",
            "recipient_name": recipient_name,
            "phone_number": phone_number,
            "country": str(address.get("country") or "Kenya").strip() or "Kenya",
            "city": city,
            "state_or_county": str(address.get("state_or_county") or "").strip() or None,
            "postal_code": str(address.get("postal_code") or "").strip() or None,
            "address_line_1": address_line_1,
            "address_line_2": str(address.get("address_line_2") or "").strip() or None,
        },
        "items": normalized_items,
        "delivery_location": delivery_location,
        "notes": str(data.get("notes") or "").strip() or None,
        "promo_code": str(data.get("promo_code") or "").strip().upper() or None,
    }


def validate_checkout_quote_payload(payload: dict | None) -> dict:
    normalized = validate_checkout_order_payload(payload)
    if "errors" in normalized:
        return normalized
    return {
        "address": normalized["address"],
        "items": normalized["items"],
        "delivery_location": normalized["delivery_location"],
        "promo_code": normalized["promo_code"],
    }


def validate_checkout_payment_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    order_id, order_error = parse_positive_int(data.get("order_id"), field_name="order_id")
    if order_error:
        errors.update(order_error)

    tracking_token = str(data.get("tracking_token") or "").strip()
    if not tracking_token:
        errors["tracking_token"] = "tracking_token is required."

    method = str(data.get("method") or "manual").strip().lower()
    phone_number = str(data.get("phone_number") or "").strip() or None

    if errors:
        return {"errors": errors}

    return {
        "order_id": order_id,
        "tracking_token": tracking_token,
        "method": method,
        "phone_number": phone_number,
    }
