from app.models import SupportTicket


def validate_support_ticket_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()
    category = str(data.get("category") or "general").strip().lower() or "general"

    if not name:
        errors["name"] = "name is required."
    if not email:
        errors["email"] = "email is required."
    if not subject:
        errors["subject"] = "subject is required."
    if not message:
        errors["message"] = "message is required."

    if errors:
        return {"errors": errors}

    return {
        "name": name,
        "email": email,
        "phone_number": str(data.get("phone_number") or "").strip() or None,
        "subject": subject,
        "message": message,
        "category": category,
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
        "status": ticket.status.value,
        "admin_note": ticket.admin_note,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }
