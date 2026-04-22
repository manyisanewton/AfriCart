from app.models import AuditLog


def log_audit_event(
    *,
    actor_user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    metadata: dict | None = None,
) -> AuditLog:
    return AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )


def serialize_audit_log(audit_log: AuditLog) -> dict:
    return {
        "id": audit_log.id,
        "actor_user_id": audit_log.actor_user_id,
        "action": audit_log.action,
        "entity_type": audit_log.entity_type,
        "entity_id": audit_log.entity_id,
        "metadata": audit_log.metadata_json or {},
        "created_at": audit_log.created_at.isoformat(),
    }
