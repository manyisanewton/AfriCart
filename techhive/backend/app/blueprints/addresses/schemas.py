def validate_address_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    required_fields = {
        "label": "label",
        "recipient_name": "recipient_name",
        "phone_number": "phone_number",
        "city": "city",
        "address_line_1": "address_line_1",
    }

    normalized = {}
    for field, label in required_fields.items():
        value = str(data.get(field, "")).strip()
        if not value:
            errors[field] = f"{label} is required."
        normalized[field] = value

    if errors:
        return {"errors": errors}

    return {
        **normalized,
        "country": str(data.get("country") or "Kenya").strip() or "Kenya",
        "state_or_county": str(data.get("state_or_county") or "").strip() or None,
        "postal_code": str(data.get("postal_code") or "").strip() or None,
        "address_line_2": str(data.get("address_line_2") or "").strip() or None,
        "is_default": bool(data.get("is_default", False)),
    }


def serialize_address(address) -> dict:
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
        "created_at": address.created_at.isoformat(),
        "updated_at": address.updated_at.isoformat(),
    }
