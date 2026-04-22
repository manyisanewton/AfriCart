def validate_create_order_payload(payload: dict | None) -> dict:
    data = payload or {}
    address_id = data.get("address_id")
    notes = data.get("notes")

    try:
        address_id = int(address_id)
        if address_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"errors": {"address_id": "address_id must be a positive integer."}}

    return {
        "address_id": address_id,
        "notes": str(notes).strip() if notes is not None else None,
    }
