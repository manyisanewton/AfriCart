from __future__ import annotations

from flask import current_app

from app.models import NotificationType, User
from app.services.notification_dispatch_service import dispatch_user_notification


def dispatch_bulk_email_campaign(
    *,
    users: list[User],
    subject: str,
    headline: str,
    message: str,
    preheader: str,
    is_marketing: bool,
    cta_label: str | None = None,
    cta_url: str | None = None,
    dry_run: bool = False,
) -> dict:
    batch_limit = current_app.config["BULK_NOTIFICATION_BATCH_SIZE"]
    limited_users = users[:batch_limit]

    if dry_run:
        return {
            "targeted_count": len(limited_users),
            "batch_limit": batch_limit,
            "mode": "dry_run",
            "results": [],
            "summary": {
                "sent": 0,
                "prepared": 0,
                "queued": 0,
                "failed": 0,
                "skipped": 0,
            },
        }

    summary = {
        "sent": 0,
        "prepared": 0,
        "queued": 0,
        "failed": 0,
        "skipped": 0,
    }
    results = []

    for user in limited_users:
        dispatch_result = dispatch_user_notification(
            user=user,
            notification_type=NotificationType.ADMIN_ANNOUNCEMENT,
            title=headline,
            message=message,
            email_subject=subject,
            email_template="admin_announcement",
            email_context={
                "headline": headline,
                "message": message,
                "title": headline,
                "preheader": preheader,
                "cta_label": cta_label,
                "cta_url": cta_url,
            },
            is_marketing=is_marketing,
            channels={"email"},
        )
        delivery = dispatch_result["deliveries"]["email"]
        status = str(delivery.get("status") or "failed").lower()
        summary[status] = summary.get(status, 0) + 1
        results.append(
            {
                "user_id": user.id,
                "email": user.email,
                "delivery": delivery,
            }
        )

    return {
        "targeted_count": len(limited_users),
        "batch_limit": batch_limit,
        "mode": "live",
        "results": results,
        "summary": summary,
    }
