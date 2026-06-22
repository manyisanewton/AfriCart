from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.integrations.base import StoredIntegrationAdapter, SystemIntegrationAdapter
from app.models import IntegrationConnection


SYSTEM_CONNECTIONS = {
    -1: {
        "name": "M-Pesa",
        "connection_type": "mpesa",
        "base_url_config_key": "MPESA_BASE_URL",
        "auth_type": "consumer_key_secret",
        "credential_source": "environment",
        "secret_env_prefix": "MPESA",
        "credential_fields": (
            ("consumer_key", "MPESA_CONSUMER_KEY"),
            ("consumer_secret", "MPESA_CONSUMER_SECRET"),
            ("shortcode", "MPESA_SHORTCODE"),
            ("passkey", "MPESA_PASSKEY"),
            ("transaction_type", "MPESA_TRANSACTION_TYPE"),
        ),
    },
    -2: {
        "name": "SMTP Email",
        "connection_type": "smtp",
        "base_url_config_key": "SMTP_HOST",
        "auth_type": "username_password",
        "credential_source": "environment",
        "secret_env_prefix": "SMTP",
        "credential_fields": (
            ("host", "SMTP_HOST"),
            ("port", "SMTP_PORT"),
            ("username", "SMTP_USERNAME"),
            ("password", "SMTP_PASSWORD"),
            ("from_email", "SMTP_FROM_EMAIL"),
            ("from_name", "SMTP_FROM_NAME"),
        ),
    },
    -3: {
        "name": "Twilio SMS",
        "connection_type": "twilio",
        "base_url_config_key": "TWILIO_API_BASE_URL",
        "auth_type": "sid_token",
        "credential_source": "environment",
        "secret_env_prefix": "TWILIO",
        "credential_fields": (
            ("account_sid", "TWILIO_ACCOUNT_SID"),
            ("auth_token", "TWILIO_AUTH_TOKEN"),
            ("from_number", "TWILIO_FROM_NUMBER"),
            ("messaging_service_sid", "TWILIO_MESSAGING_SERVICE_SID"),
        ),
    },
    -4: {
        "name": "Sentry Monitoring",
        "connection_type": "sentry",
        "base_url_config_key": "SENTRY_DSN",
        "auth_type": "dsn",
        "credential_source": "environment",
        "secret_env_prefix": "SENTRY",
        "credential_fields": (
            ("dsn", "SENTRY_DSN"),
            ("environment", "SENTRY_ENVIRONMENT"),
        ),
    },
}


def list_integration_adapters():
    stored = [
        StoredIntegrationAdapter(connection)
        for connection in IntegrationConnection.query.order_by(IntegrationConnection.name.asc()).all()
    ]
    system = [
        SystemIntegrationAdapter(definition=SYSTEM_CONNECTIONS[connection_id], connection_id=connection_id, config=current_app.config)
        for connection_id in SYSTEM_CONNECTIONS
    ]
    return system + stored


def get_integration_adapter(connection_id: int):
    if connection_id in SYSTEM_CONNECTIONS:
        return SystemIntegrationAdapter(definition=SYSTEM_CONNECTIONS[connection_id], connection_id=connection_id, config=current_app.config)
    connection = db.session.get(IntegrationConnection, connection_id)
    if connection is None:
        return None
    return StoredIntegrationAdapter(connection)
