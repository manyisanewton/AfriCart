from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.blueprints.notifications.push import create_notification
from app.blueprints.payments.helpers import dump_provider_response
from app.blueprints.payments.mpesa import MpesaGatewayError, query_mpesa_payment_status
from app.models import NotificationType, Payment, PaymentMethod, PaymentStatus


def build_payment_reconciliation_deadline(timeout_minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)


def build_next_reconciliation_deadline(retry_delay_minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=retry_delay_minutes)


def reconcile_stale_mpesa_payments(
    *,
    limit: int,
    max_attempts: int,
    retry_delay_minutes: int,
) -> dict[str, list[Payment]]:
    now = datetime.now(timezone.utc)
    stale_payments = (
        Payment.query.filter(
            Payment.method == PaymentMethod.MPESA,
            Payment.status == PaymentStatus.PENDING,
            Payment.reconciliation_due_at.isnot(None),
            Payment.reconciliation_due_at <= now,
        )
        .order_by(Payment.reconciliation_due_at.asc(), Payment.id.asc())
        .limit(limit)
        .all()
    )

    awaiting_confirmation: list[Payment] = []
    timed_out: list[Payment] = []
    provider_failed: list[Payment] = []
    manual_review: list[Payment] = []

    for payment in stale_payments:
        payment.reconciliation_attempts += 1
        provider_state = {"state": "pending", "raw": {"provider": "mpesa", "reason": "default_pending"}}
        try:
            provider_state = query_mpesa_payment_status(payment)
        except MpesaGatewayError as exc:
            provider_state = {
                "state": "unavailable",
                "failure_code": "provider_status_unavailable",
                "failure_message": str(exc),
                "raw": {"provider": "mpesa", "error": str(exc)},
            }

        payment.provider_response = dump_provider_response(provider_state.get("raw"))

        if provider_state["state"] == "failed":
            payment.status = PaymentStatus.FAILED
            payment.failure_code = provider_state["failure_code"]
            payment.failure_message = provider_state["failure_message"]
            payment.processed_at = now
            payment.reconciliation_due_at = None
            create_notification(
                payment.order.user_id,
                NotificationType.PAYMENT_FAILED,
                "Payment failed",
                f"Payment {payment.reference} was marked as failed after M-Pesa status verification.",
            )
            provider_failed.append(payment)
            continue

        if provider_state["state"] == "manual_review":
            payment.failure_code = provider_state["failure_code"]
            payment.failure_message = provider_state["failure_message"]
            payment.processed_at = now
            payment.reconciliation_due_at = None
            create_notification(
                payment.order.user_id,
                NotificationType.PAYMENT_FAILED,
                "Payment requires review",
                f"Payment {payment.reference} needs manual review after M-Pesa status verification.",
            )
            manual_review.append(payment)
            continue

        if payment.reconciliation_attempts < max_attempts:
            payment.failure_code = "awaiting_provider_confirmation"
            payment.failure_message = (
                "Awaiting M-Pesa provider confirmation after the callback window elapsed."
            )
            payment.reconciliation_due_at = build_next_reconciliation_deadline(
                retry_delay_minutes
            )
            awaiting_confirmation.append(payment)
            continue

        payment.status = PaymentStatus.FAILED
        payment.failure_code = "reconciliation_timeout"
        payment.failure_message = "M-Pesa payment timed out before callback confirmation."
        payment.processed_at = now
        payment.reconciliation_due_at = None
        create_notification(
            payment.order.user_id,
            NotificationType.PAYMENT_FAILED,
            "Payment reconciliation timeout",
            f"Payment {payment.reference} was marked as failed after callback timeout.",
        )
        timed_out.append(payment)

    return {
        "awaiting_confirmation": awaiting_confirmation,
        "provider_failed": provider_failed,
        "manual_review": manual_review,
        "timed_out": timed_out,
    }
