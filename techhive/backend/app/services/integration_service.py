from __future__ import annotations

from app.extensions import db
from app.integrations import get_integration_adapter, list_integration_adapters
from app.models import IntegrationLog


def serialize_integration_connection(connection) -> dict:
    adapter = get_integration_adapter(connection.id)
    return adapter.serialize() if adapter else {}


def list_all_connections() -> list[dict]:
    return [adapter.serialize() for adapter in list_integration_adapters()]


def get_connection_adapter(connection_id: int):
    return get_integration_adapter(connection_id)


def get_connection_payload(connection_id: int) -> dict | None:
    adapter = get_connection_adapter(connection_id)
    return adapter.serialize() if adapter else None


def append_integration_log(
    *,
    connection_id: int,
    connection_name: str,
    direction: str,
    entity_type: str,
    external_reference: str | None,
    status: str,
    payload_excerpt: dict | None = None,
    error_message: str | None = None,
) -> IntegrationLog:
    log = IntegrationLog(
        connection_id=connection_id,
        connection_name=connection_name,
        direction=direction,
        entity_type=entity_type,
        external_reference=external_reference,
        status=status,
        payload_excerpt=payload_excerpt,
        error_message=error_message,
    )
    db.session.add(log)
    return log
