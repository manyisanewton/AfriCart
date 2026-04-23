from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models import Payment, PaymentMethod, PaymentStatus


def collect_payment_metrics() -> dict:
    payment_counts = (
        db.session.query(Payment.method, Payment.status, func.count(Payment.id))
        .group_by(Payment.method, Payment.status)
        .all()
    )
    reconciliation_counts = (
        db.session.query(Payment.failure_code, func.count(Payment.id))
        .filter(Payment.failure_code.isnot(None))
        .group_by(Payment.failure_code)
        .all()
    )
    now = datetime.now(timezone.utc)
    overdue_pending_count = (
        db.session.query(func.count(Payment.id))
        .filter(
            Payment.method == PaymentMethod.MPESA,
            Payment.status == PaymentStatus.PENDING,
            Payment.reconciliation_due_at.isnot(None),
            Payment.reconciliation_due_at <= now,
        )
        .scalar()
        or 0
    )

    return {
        "payment_counts": [
            {
                "method": method.value if hasattr(method, "value") else str(method),
                "status": status.value if hasattr(status, "value") else str(status),
                "count": int(count),
            }
            for method, status, count in payment_counts
        ],
        "reconciliation_counts": [
            {
                "state": str(failure_code),
                "count": int(count),
            }
            for failure_code, count in reconciliation_counts
        ],
        "overdue_pending_count": int(overdue_pending_count),
    }


def render_payment_metrics_lines() -> list[str]:
    metrics = collect_payment_metrics()
    lines = [
        "# HELP techhive_payments_total Count of payments by method and status.",
        "# TYPE techhive_payments_total gauge",
    ]
    for item in metrics["payment_counts"]:
        lines.append(
            f'techhive_payments_total{{method="{item["method"]}",status="{item["status"]}"}} {item["count"]}'
        )

    lines.extend(
        [
            "# HELP techhive_payment_reconciliation_total Count of payment reconciliation states.",
            "# TYPE techhive_payment_reconciliation_total gauge",
        ]
    )
    for item in metrics["reconciliation_counts"]:
        lines.append(
            f'techhive_payment_reconciliation_total{{state="{item["state"]}"}} {item["count"]}'
        )

    lines.extend(
        [
            "# HELP techhive_mpesa_pending_overdue_total Count of overdue pending M-Pesa payments.",
            "# TYPE techhive_mpesa_pending_overdue_total gauge",
            f'techhive_mpesa_pending_overdue_total {metrics["overdue_pending_count"]}',
        ]
    )
    return lines
