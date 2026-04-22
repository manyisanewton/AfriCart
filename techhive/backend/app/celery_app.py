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
    )

    class FlaskTask(celery_app.Task):
        def __call__(self, *args: Any, **kwargs: Any):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    return celery_app


def get_task_queue_status(app: Flask) -> dict:
    return {
        "enabled": app.config["TASK_QUEUE_ENABLED"],
        "celery_installed": Celery is not None,
        "broker_url": app.config["CELERY_BROKER_URL"],
        "result_backend": app.config["CELERY_RESULT_BACKEND"],
        "task_always_eager": app.config["CELERY_TASK_ALWAYS_EAGER"],
    }
