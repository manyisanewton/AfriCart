from app.models import SupportTicket


def validate_support_ticket_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()
    category = str(data.get("category") or "general").strip().lower() or "general"
    context_data = data.get("context_data")

    if not name:
        errors["name"] = "name is required."
    if not email:
        errors["email"] = "email is required."
    if not subject:
        errors["subject"] = "subject is required."
    if not message:
        errors["message"] = "message is required."
    if context_data not in (None, "") and not isinstance(context_data, dict):
        errors["context_data"] = "context_data must be an object."

    if errors:
        return {"errors": errors}

    normalized_context = None
    if isinstance(context_data, dict):
        normalized_context = {}
        for key, value in context_data.items():
            normalized_key = str(key or "").strip()
            if not normalized_key:
                continue
            if value in (None, ""):
                continue
            normalized_context[normalized_key] = str(value).strip()
        normalized_context = normalized_context or None

    return {
        "name": name,
        "email": email,
        "phone_number": str(data.get("phone_number") or "").strip() or None,
        "subject": subject,
        "message": message,
        "category": category,
        "context_data": normalized_context,
    }


def serialize_support_ticket(ticket: SupportTicket) -> dict:
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "name": ticket.name,
        "email": ticket.email,
        "phone_number": ticket.phone_number,
        "subject": ticket.subject,
        "message": ticket.message,
        "category": ticket.category,
        "context_data": ticket.context_data or {},
        "status": ticket.status.value,
        "admin_note": ticket.admin_note,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }
