from __future__ import annotations

from app.extensions import db
from app.models import NotificationType, Order, Refund, SupportTicket
from app.services.email_service import send_email
from app.services.notification_dispatch_service import dispatch_user_notification
from app.utils.helpers import format_money


def notify_refund_requested(refund: Refund) -> None:
    order = refund.order or db.session.get(Order, refund.order_id)
    dispatch_user_notification(
        user=order.user,
        notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
        title="Refund requested",
        message=f"Your refund request for order {order.order_number} has been received.",
        email_subject=f"Refund request received for order {order.order_number}",
        email_template="refund_status",
        email_context={
            "order_number": order.order_number,
            "refund_amount": format_money(refund.amount),
            "status_label": "Requested",
            "status_tone": "info",
            "reason_text": refund.reason,
            "headline": "Your refund request has been received",
            "preheader": f"We are reviewing the refund request for order {order.order_number}.",
        },
    )


def notify_refund_updated(refund: Refund) -> None:
    order = refund.order or db.session.get(Order, refund.order_id)
    status_label = refund.status.value.replace("_", " ").title()
    tone = "success" if refund.status.value == "processed" else "info"
    if refund.status.value == "rejected":
        tone = "attention"

    dispatch_user_notification(
        user=order.user,
        notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
        title=f"Refund {status_label.lower()}",
        message=f"Your refund for order {order.order_number} is now {status_label.lower()}.",
        email_subject=f"Refund update for order {order.order_number}",
        email_template="refund_status",
        email_context={
            "order_number": order.order_number,
            "refund_amount": format_money(refund.amount),
            "status_label": status_label,
            "status_tone": tone,
            "reason_text": refund.reason,
            "admin_note": refund.admin_note,
            "headline": "Your refund request has been updated",
            "preheader": f"Refund status for order {order.order_number}: {status_label}.",
        },
    )


def notify_support_ticket_created(ticket: SupportTicket) -> None:
    email_context = {
        "ticket_subject": ticket.subject,
        "ticket_category": ticket.category,
        "ticket_status": ticket.status.value.replace("_", " ").title(),
        "ticket_message": ticket.message,
        "headline": "We received your support request",
        "preheader": f"Ticket received: {ticket.subject}",
    }

    if ticket.user is not None:
        dispatch_user_notification(
            user=ticket.user,
            notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
            title="Support request received",
            message=f"We received your support request: {ticket.subject}.",
            email_subject=f"Support request received: {ticket.subject}",
            email_template="support_ticket",
            email_context=email_context,
        )
        return

    send_email(
        to_email=ticket.email,
        subject=f"Support request received: {ticket.subject}",
        template="support_ticket",
        context={
            "user_name": ticket.name,
            **email_context,
        },
    )


def notify_support_ticket_updated(ticket: SupportTicket) -> None:
    status_label = ticket.status.value.replace("_", " ").title()
    tone = "success" if ticket.status.value in {"resolved", "closed"} else "info"
    if ticket.status.value == "open":
        tone = "attention"

    email_context = {
        "ticket_subject": ticket.subject,
        "ticket_category": ticket.category,
        "ticket_status": status_label,
        "ticket_message": ticket.message,
        "admin_note": ticket.admin_note,
        "status_tone": tone,
        "headline": "Your support ticket has an update",
        "preheader": f"Support status: {status_label}",
    }

    if ticket.user is not None:
        dispatch_user_notification(
            user=ticket.user,
            notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
            title=f"Support ticket {status_label.lower()}",
            message=f"Your support ticket '{ticket.subject}' is now {status_label.lower()}.",
            email_subject=f"Support update: {ticket.subject}",
            email_template="support_ticket",
            email_context=email_context,
        )
        return

    send_email(
        to_email=ticket.email,
        subject=f"Support update: {ticket.subject}",
        template="support_ticket",
        context={
            "user_name": ticket.name,
            **email_context,
        },
    )
