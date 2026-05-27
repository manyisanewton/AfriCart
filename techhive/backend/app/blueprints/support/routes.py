from flask import g, jsonify

from app.blueprints.auth.helpers import validation_error
from app.blueprints.support import support_bp
from app.blueprints.support.schemas import serialize_support_ticket, validate_support_ticket_payload
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import SupportTicket
from app.services.audit_service import log_request_audit_event
from app.services.major_notification_service import notify_support_ticket_created
from app.utils.api import get_json_payload


@support_bp.post("/tickets")
def create_support_ticket():
    """
    Create a support ticket.
    ---
    tags:
      - Support
    responses:
      201:
        description: Support ticket created.
    """
    payload = validate_support_ticket_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    user_id = getattr(g, "current_user", None).id if hasattr(g, "current_user") else None
    ticket = SupportTicket(user_id=user_id, **payload)
    db.session.add(ticket)
    db.session.flush()
    audit_log = log_request_audit_event(
        actor_user_id=user_id,
        action="customer.support_ticket_created",
        entity_type="support_ticket",
        entity_id=ticket.id,
        message="Customer created a support ticket.",
        target_repr=ticket.subject,
        metadata={"category": ticket.category, "email": ticket.email},
    )
    if audit_log is not None:
        db.session.add(audit_log)
    notify_support_ticket_created(ticket)
    db.session.commit()
    return jsonify({"item": serialize_support_ticket(ticket)}), 201
