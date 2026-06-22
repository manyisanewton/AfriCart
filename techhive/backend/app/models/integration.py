from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntegrationConnection(db.Model):
    __tablename__ = "integration_connections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"), nullable=True, index=True)
    connection_type = db.Column(db.String(80), nullable=False, index=True)
    base_url = db.Column(db.String(255), nullable=False)
    auth_type = db.Column(db.String(80), nullable=False)
    credential_source = db.Column(db.String(80), nullable=False, default="env")
    secret_env_prefix = db.Column(db.String(120), nullable=True)
    credential_values = db.Column(db.JSON, nullable=True)
    default_company = db.Column(db.String(160), nullable=True)
    default_warehouse = db.Column(db.String(160), nullable=True)
    poll_interval_minutes = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="draft")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_successful_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_failed_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    partner = db.relationship("Partner", lazy="selectin")


class IntegrationLog(db.Model):
    __tablename__ = "integration_logs"

    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, nullable=False, index=True)
    connection_name = db.Column(db.String(160), nullable=False)
    direction = db.Column(db.String(40), nullable=False, default="system")
    entity_type = db.Column(db.String(80), nullable=False)
    external_reference = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(40), nullable=False)
    payload_excerpt = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
