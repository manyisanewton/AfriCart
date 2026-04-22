from __future__ import annotations

from importlib import import_module
from types import ModuleType
from uuid import uuid4

from flask import Flask, g, request


def initialize_error_monitoring(app: Flask) -> bool:
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        app.logger.info("Sentry is disabled because SENTRY_DSN is not configured.")
        return False

    try:
        sentry_sdk = _import_module("sentry_sdk")
        flask_module = _import_module("sentry_sdk.integrations.flask")
    except ImportError:
        app.logger.warning("Sentry SDK is not installed; skipping error monitoring setup.")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=app.config["SENTRY_ENVIRONMENT"],
        traces_sample_rate=app.config["SENTRY_TRACES_SAMPLE_RATE"],
        integrations=[flask_module.FlaskIntegration()],
    )
    app.logger.info("Sentry error monitoring initialized.")
    return True


def register_request_context(app: Flask) -> None:
    @app.before_request
    def attach_request_id():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid4())

    @app.after_request
    def append_request_id_header(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", str(uuid4()))
        return response


def _import_module(path: str) -> ModuleType:
    return import_module(path)
