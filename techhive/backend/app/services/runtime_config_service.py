from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from flask import Flask

from app.models import PaymentMethod


DEFAULT_SECRET_VALUES = {"dev-secret-key", "change-me", "secret"}


@dataclass
class RuntimeConfigReport:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class RuntimeConfigurationError(RuntimeError):
    def __init__(self, errors: list[str]):
        super().__init__("Invalid runtime configuration: " + "; ".join(errors))
        self.errors = errors


def collect_runtime_config_report(app: Flask) -> RuntimeConfigReport:
    errors: list[str] = []
    warnings: list[str] = []
    config = app.config

    is_testing = bool(config.get("TESTING"))
    is_debug = bool(config.get("DEBUG"))
    environment = "production" if not is_testing and not is_debug else (
        "testing" if is_testing else "development"
    )

    secret_key = str(config.get("SECRET_KEY") or "")
    jwt_secret = str(config.get("JWT_SECRET_KEY") or "")
    db_uri = str(config.get("SQLALCHEMY_DATABASE_URI") or "")
    callback_base = str(config.get("PAYMENT_CALLBACK_BASE_URL") or "")
    cors_origins = str(config.get("CORS_ALLOWED_ORIGINS") or "")
    enabled_payment_methods = {
        str(value).strip().lower()
        for value in config.get("PAYMENT_ENABLED_METHODS", ())
        if str(value).strip()
    }
    primary_payment_method = str(config.get("PAYMENT_PRIMARY_METHOD") or "").strip().lower()
    valid_payment_methods = {member.value for member in PaymentMethod}

    if environment == "production":
        if secret_key in DEFAULT_SECRET_VALUES:
            errors.append("SECRET_KEY must be set to a non-default value in production.")
        if jwt_secret in DEFAULT_SECRET_VALUES or jwt_secret == secret_key:
            errors.append("JWT_SECRET_KEY must be set independently in production.")
        if db_uri.startswith("sqlite:"):
            errors.append("SQLite is not allowed as the production database backend.")
        if not _is_https_url(callback_base):
            errors.append("PAYMENT_CALLBACK_BASE_URL must use HTTPS in production.")
        if config.get("PAYMENTS_ALLOW_SIMULATION"):
            errors.append("PAYMENTS_ALLOW_SIMULATION must be disabled in production.")
        if config.get("MPESA_ALLOW_UNSIGNED_CALLBACKS"):
            errors.append("MPESA_ALLOW_UNSIGNED_CALLBACKS must be disabled in production.")
        if cors_origins.strip() == "*":
            errors.append("CORS_ALLOWED_ORIGINS must be restricted in production.")
        if not config.get("SENTRY_DSN"):
            warnings.append("SENTRY_DSN is not configured for production monitoring.")
    else:
        if secret_key in DEFAULT_SECRET_VALUES:
            warnings.append("SECRET_KEY is still using a development default.")
        if config.get("PAYMENTS_ALLOW_SIMULATION"):
            warnings.append("PAYMENTS_ALLOW_SIMULATION is enabled.")
        if config.get("MPESA_ALLOW_UNSIGNED_CALLBACKS"):
            warnings.append("MPESA_ALLOW_UNSIGNED_CALLBACKS is enabled.")
        if db_uri.startswith("sqlite:"):
            warnings.append("SQLite is being used for local runtime.")

    if not enabled_payment_methods:
        errors.append("PAYMENT_ENABLED_METHODS must include at least one payment method.")
    else:
        invalid_methods = sorted(enabled_payment_methods - valid_payment_methods)
        if invalid_methods:
            errors.append(
                "PAYMENT_ENABLED_METHODS contains invalid methods: "
                + ", ".join(invalid_methods)
                + "."
            )
    if primary_payment_method and primary_payment_method not in valid_payment_methods:
        errors.append("PAYMENT_PRIMARY_METHOD must be a supported payment method.")
    elif primary_payment_method and primary_payment_method not in enabled_payment_methods:
        errors.append("PAYMENT_PRIMARY_METHOD must also be listed in PAYMENT_ENABLED_METHODS.")
    elif enabled_payment_methods == {PaymentMethod.MPESA.value}:
        warnings.append("Payments are narrowed to M-Pesa only.")

    smtp_status = _validate_smtp_config(config, strict=environment == "production")
    twilio_status = _validate_twilio_config(config, strict=environment == "production")
    if smtp_status["error"]:
        errors.append(smtp_status["error"])
    elif smtp_status["warning"]:
        warnings.append(smtp_status["warning"])
    if twilio_status["error"]:
        errors.append(twilio_status["error"])
    elif twilio_status["warning"]:
        warnings.append(twilio_status["warning"])

    if config.get("TASK_QUEUE_ENABLED") and not config.get("CELERY_BROKER_URL"):
        errors.append("TASK_QUEUE_ENABLED requires CELERY_BROKER_URL.")

    return RuntimeConfigReport(errors=errors, warnings=warnings)


def validate_runtime_configuration(app: Flask) -> RuntimeConfigReport:
    report = collect_runtime_config_report(app)
    app.extensions["runtime_config_report"] = report.to_dict()

    for warning in report.warnings:
        app.logger.warning("Runtime configuration warning: %s", warning)

    if not report.is_valid:
        for error in report.errors:
            app.logger.error("Runtime configuration error: %s", error)
        if not app.config.get("TESTING") and not app.config.get("DEBUG"):
            raise RuntimeConfigurationError(report.errors)

    return report


def get_runtime_config_report(app: Flask) -> dict:
    report = app.extensions.get("runtime_config_report")
    if report is None:
        report = validate_runtime_configuration(app).to_dict()
        app.extensions["runtime_config_report"] = report
    return report


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate_smtp_config(config: dict, *, strict: bool) -> dict[str, str | None]:
    host = config.get("SMTP_HOST")
    username = config.get("SMTP_USERNAME")
    password = config.get("SMTP_PASSWORD")
    from_email = config.get("SMTP_FROM_EMAIL")
    if not any([host, username, password]):
        return {
            "error": None,
            "warning": None if strict else "SMTP delivery is not configured; emails will stay in prepared mode.",
        }
    if not all([host, username, password, from_email]):
        return {
            "error": "SMTP configuration is incomplete." if strict else None,
            "warning": None if strict else "SMTP configuration is incomplete.",
        }
    return {"error": None, "warning": None}


def _validate_twilio_config(config: dict, *, strict: bool) -> dict[str, str | None]:
    sid = config.get("TWILIO_ACCOUNT_SID")
    token = config.get("TWILIO_AUTH_TOKEN")
    from_number = config.get("TWILIO_FROM_NUMBER")
    service_sid = config.get("TWILIO_MESSAGING_SERVICE_SID")
    if not any([sid, token, from_number, service_sid]):
        return {
            "error": None,
            "warning": None if strict else "Twilio SMS delivery is not configured; SMS will stay in prepared mode.",
        }
    if not sid or not token or not (from_number or service_sid):
        return {
            "error": "Twilio configuration is incomplete." if strict else None,
            "warning": None if strict else "Twilio configuration is incomplete.",
        }
    return {"error": None, "warning": None}
