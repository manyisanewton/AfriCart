from app.extensions import db
from app.services.payment_reconciliation_service import reconcile_stale_mpesa_payments


def run_stale_mpesa_reconciliation(
    *,
    limit: int = 100,
    max_attempts: int = 2,
    retry_delay_minutes: int = 5,
) -> dict:
    results = reconcile_stale_mpesa_payments(
        limit=limit,
        max_attempts=max_attempts,
        retry_delay_minutes=retry_delay_minutes,
    )
    db.session.commit()
    return {
        "count": (
            len(results["awaiting_confirmation"])
            + len(results["provider_failed"])
            + len(results["manual_review"])
            + len(results["timed_out"])
        ),
        "awaiting_confirmation_ids": [
            payment.id for payment in results["awaiting_confirmation"]
        ],
        "provider_failed_ids": [payment.id for payment in results["provider_failed"]],
        "manual_review_ids": [payment.id for payment in results["manual_review"]],
        "timed_out_ids": [payment.id for payment in results["timed_out"]],
    }
