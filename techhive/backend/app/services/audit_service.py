from flask import request

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


def build_request_audit_metadata(*, message: str | None = None, target_repr: str | None = None, metadata: dict | None = None) -> dict:
    payload = dict(metadata or {})
    payload.setdefault("status", "success")
    payload.setdefault("request_method", request.method)
    payload.setdefault("path", request.path)
    payload.setdefault("ip_address", request.headers.get("X-Forwarded-For", request.remote_addr))
    payload.setdefault("user_agent", request.headers.get("User-Agent", ""))
    if message:
        payload.setdefault("message", message)
    if target_repr:
        payload.setdefault("target_repr", target_repr)
    return payload


def log_request_audit_event(
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    message: str | None = None,
    target_repr: str | None = None,
    metadata: dict | None = None,
) -> AuditLog | None:
    if actor_user_id is None:
        return None

    return log_audit_event(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=build_request_audit_metadata(
            message=message,
            target_repr=target_repr,
            metadata=metadata,
        ),
    )


def serialize_audit_log(audit_log: AuditLog) -> dict:
    metadata = audit_log.metadata_json or {}
    actor_user = audit_log.actor_user
    status = str(metadata.get("status") or "success")
    target_repr = metadata.get("target_repr")
    if not target_repr and audit_log.entity_type and audit_log.entity_id:
        target_repr = f"{audit_log.entity_type} #{audit_log.entity_id}"

    return {
        "id": audit_log.id,
        "actor_user_id": audit_log.actor_user_id,
        "actor_id": audit_log.actor_user_id,
        "actor_email": actor_user.email if actor_user is not None else "",
        "actor_role": actor_user.role.value if actor_user is not None else "",
        "action": audit_log.action,
        "event_type": audit_log.action,
        "status": status,
        "entity_type": audit_log.entity_type,
        "target_type": audit_log.entity_type,
        "entity_id": audit_log.entity_id,
        "target_id": str(audit_log.entity_id) if audit_log.entity_id is not None else "",
        "target_repr": target_repr or "",
        "message": str(metadata.get("message") or ""),
        "request_method": str(metadata.get("request_method") or ""),
        "path": str(metadata.get("path") or ""),
        "ip_address": metadata.get("ip_address"),
        "user_agent": str(metadata.get("user_agent") or ""),
        "metadata": metadata,
        "created_at": audit_log.created_at.isoformat(),
    }
