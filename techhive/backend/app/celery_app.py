from __future__ import annotations

from typing import Any

from flask import Flask


try:
    from celery import Celery
except ImportError:  # pragma: no cover - optional dependency
    Celery = None


def create_celery_app(app: Flask | None = None):
    if Celery is None or app is None:
        return None

    celery_app = Celery(
        app.import_name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_RESULT_BACKEND"],
    )
    celery_app.conf.update(
        task_always_eager=app.config["CELERY_TASK_ALWAYS_EAGER"],
        beat_schedule={
            "payments.reconcile-stale-mpesa": {
                "task": "payments.reconcile_stale_mpesa",
                "schedule": app.config["MPESA_RECONCILIATION_SCHEDULE_MINUTES"] * 60,
                "kwargs": {
                    "limit": app.config["MPESA_RECONCILIATION_BATCH_LIMIT"],
                    "max_attempts": app.config["MPESA_RECONCILIATION_MAX_ATTEMPTS"],
                    "retry_delay_minutes": app.config[
                        "MPESA_RECONCILIATION_RETRY_DELAY_MINUTES"
                    ],
                },
            }
        },
    )

    class FlaskTask(celery_app.Task):
        def __call__(self, *args: Any, **kwargs: Any):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask

    @celery_app.task(name="payments.reconcile_stale_mpesa")
    def reconcile_stale_mpesa_task(
        *,
        limit: int | None = None,
        max_attempts: int | None = None,
        retry_delay_minutes: int | None = None,
    ):
        from app.tasks.payment_tasks import run_stale_mpesa_reconciliation

        return run_stale_mpesa_reconciliation(
            limit=limit or app.config["MPESA_RECONCILIATION_BATCH_LIMIT"],
            max_attempts=max_attempts or app.config["MPESA_RECONCILIATION_MAX_ATTEMPTS"],
            retry_delay_minutes=retry_delay_minutes
            or app.config["MPESA_RECONCILIATION_RETRY_DELAY_MINUTES"],
        )

    return celery_app


def get_task_queue_status(app: Flask) -> dict:
    return {
        "enabled": app.config["TASK_QUEUE_ENABLED"],
        "celery_installed": Celery is not None,
        "broker_url": app.config["CELERY_BROKER_URL"],
        "result_backend": app.config["CELERY_RESULT_BACKEND"],
        "task_always_eager": app.config["CELERY_TASK_ALWAYS_EAGER"],
        "schedules": {
            "payments.reconcile_stale_mpesa": {
                "enabled": app.config["TASK_QUEUE_ENABLED"],
                "interval_minutes": app.config["MPESA_RECONCILIATION_SCHEDULE_MINUTES"],
                "batch_limit": app.config["MPESA_RECONCILIATION_BATCH_LIMIT"],
                "max_attempts": app.config["MPESA_RECONCILIATION_MAX_ATTEMPTS"],
                "retry_delay_minutes": app.config[
                    "MPESA_RECONCILIATION_RETRY_DELAY_MINUTES"
                ],
            }
        },
    }
