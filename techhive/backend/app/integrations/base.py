from __future__ import annotations

import os
from abc import ABC
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.extensions import db
from app.models import Product


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntegrationAdapter(ABC):
    supports_test = True
    supports_preview = False
    supports_import = False
    supports_stock_sync = False

    def __init__(
        self,
        *,
        connection_id: int,
        name: str,
        connection_type: str,
        base_url: str,
        auth_type: str,
        credential_source: str,
        secret_env_prefix: str | None,
        credentials: dict[str, Any],
        credentials_read_only: bool,
        partner_id: int | None = None,
        partner_name: str | None = None,
        default_company: str | None = None,
        default_warehouse: str | None = None,
        poll_interval_minutes: int | None = None,
        status: str = "draft",
        is_active: bool = True,
        last_successful_sync_at: datetime | None = None,
        last_failed_sync_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.connection_id = connection_id
        self.name = name
        self.connection_type = connection_type
        self.base_url = base_url
        self.auth_type = auth_type
        self.credential_source = credential_source
        self.secret_env_prefix = secret_env_prefix
        self.credentials = credentials
        self.credentials_read_only = credentials_read_only
        self.partner_id = partner_id
        self.partner_name = partner_name
        self.default_company = default_company
        self.default_warehouse = default_warehouse
        self.poll_interval_minutes = poll_interval_minutes
        self.status = status
        self.is_active = is_active
        self.last_successful_sync_at = last_successful_sync_at
        self.last_failed_sync_at = last_failed_sync_at
        self.created_at = created_at
        self.updated_at = updated_at

    def _has_non_empty_credential(self, *keys: str) -> bool:
        for key in keys:
            value = self.credentials.get(key)
            if value not in (None, ""):
                return True
        return False

    def _has_api_key(self) -> bool:
        if self.secret_env_prefix:
            return bool(
                os.getenv(f"{self.secret_env_prefix}_API_KEY")
                or os.getenv(f"{self.secret_env_prefix}_USERNAME")
                or os.getenv(f"{self.secret_env_prefix}_ACCOUNT_SID")
            ) or self._has_non_empty_credential("api_key", "username", "account_sid", "client_id", "organization_id")
        return self._has_non_empty_credential("api_key", "username", "account_sid", "client_id", "organization_id")

    def _has_api_secret(self) -> bool:
        if self.secret_env_prefix:
            return bool(
                os.getenv(f"{self.secret_env_prefix}_API_SECRET")
                or os.getenv(f"{self.secret_env_prefix}_PASSWORD")
                or os.getenv(f"{self.secret_env_prefix}_AUTH_TOKEN")
                or os.getenv(f"{self.secret_env_prefix}_PASSKEY")
                or os.getenv(f"{self.secret_env_prefix}_CONSUMER_SECRET")
                or os.getenv(f"{self.secret_env_prefix}_REFRESH_TOKEN")
            ) or self._has_non_empty_credential(
                "api_secret",
                "password",
                "auth_token",
                "passkey",
                "consumer_secret",
                "client_secret",
                "refresh_token",
                "access_token",
            )
        return self._has_non_empty_credential(
            "api_secret",
            "password",
            "auth_token",
            "passkey",
            "consumer_secret",
            "client_secret",
            "refresh_token",
            "access_token",
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.connection_id,
            "name": self.name,
            "partner": self.partner_id,
            "partner_name": self.partner_name,
            "connection_type": self.connection_type,
            "base_url": self.base_url,
            "auth_type": self.auth_type,
            "credential_source": self.credential_source,
            "secret_env_prefix": self.secret_env_prefix,
            "credentials": {
                "values": self.credentials,
                "read_only": self.credentials_read_only,
                "source": self.credential_source,
            },
            "has_api_key": self._has_api_key(),
            "has_api_secret": self._has_api_secret(),
            "default_company": self.default_company,
            "default_warehouse": self.default_warehouse,
            "poll_interval_minutes": self.poll_interval_minutes,
            "status": self.status,
            "is_active": self.is_active,
            "last_successful_sync_at": self.last_successful_sync_at.isoformat() if self.last_successful_sync_at else None,
            "last_failed_sync_at": self.last_failed_sync_at.isoformat() if self.last_failed_sync_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "supports_test": self.supports_test,
            "supports_preview": self.supports_preview,
            "supports_import": self.supports_import,
            "supports_stock_sync": self.supports_stock_sync,
        }

    def test_connection(self) -> tuple[bool, dict[str, Any]]:
        base_url = str(self.base_url or "").strip()
        has_api_key = self._has_api_key()
        has_api_secret = self._has_api_secret()
        parsed = urlparse(base_url) if base_url else None

        if self.connection_type in {"smtp", "sentry"}:
            ok = bool(base_url)
            return ok, {"validated_locally": ok, "base_value_present": bool(base_url)}

        ok = bool(base_url and parsed and parsed.scheme in {"http", "https"} and parsed.netloc and (has_api_key or has_api_secret))
        return ok, {
            "validated_locally": ok,
            "base_url": base_url,
            "has_api_key": has_api_key,
            "has_api_secret": has_api_secret,
        }

    def preview_catalog_records(self, resource: str, limit: int) -> dict[str, Any]:
        products = Product.query.order_by(Product.created_at.desc(), Product.id.desc()).limit(limit).all()
        if resource == "stock":
            records = [
                {
                    "sku": product.sku,
                    "name": product.name,
                    "stock_quantity": product.stock_quantity,
                    "low_stock_threshold": product.low_stock_threshold,
                }
                for product in products
            ]
        elif resource == "prices":
            records = [
                {
                    "sku": product.sku,
                    "name": product.name,
                    "price": str(product.price),
                    "currency": product.currency,
                }
                for product in products
            ]
        else:
            records = [
                {
                    "sku": product.sku,
                    "name": product.name,
                    "vendor": product.vendor.business_name if product.vendor else "",
                    "category": product.category.name if product.category else "",
                    "price": str(product.price),
                    "in_stock": product.in_stock,
                }
                for product in products
            ]
        return {
            "resource": resource,
            "count": len(records),
            "records": records,
            "source": self.connection_type,
        }

    def import_catalog(self, *, include_stock: bool) -> dict[str, Any]:
        return {
            "mode": "dry_run_local_preview",
            "connection_type": self.connection_type,
            "products_seen": Product.query.count(),
            "stock_included": include_stock,
            "synced_at": utc_now().isoformat(),
        }

    def sync_stock(self) -> dict[str, Any]:
        return {
            "mode": "local_refresh",
            "connection_type": self.connection_type,
            "products_seen": Product.query.count(),
            "synced_at": utc_now().isoformat(),
        }

    def on_test_result(self, *, ok: bool) -> None:
        self.status = "active" if ok else "error"

    def on_import_success(self) -> None:
        self.status = "active"

    def on_stock_sync_success(self) -> None:
        self.status = "active"

    def persist_state(self) -> None:
        return None


class StoredIntegrationAdapter(IntegrationAdapter):
    def __init__(self, connection) -> None:
        super().__init__(
            connection_id=connection.id,
            name=connection.name,
            connection_type=connection.connection_type,
            base_url=connection.base_url,
            auth_type=connection.auth_type,
            credential_source=connection.credential_source,
            secret_env_prefix=connection.secret_env_prefix,
            credentials=connection.credential_values or {},
            credentials_read_only=False,
            partner_id=connection.partner.id if connection.partner else None,
            partner_name=connection.partner.name if connection.partner else None,
            default_company=connection.default_company,
            default_warehouse=connection.default_warehouse,
            poll_interval_minutes=connection.poll_interval_minutes,
            status=connection.status,
            is_active=connection.is_active,
            last_successful_sync_at=connection.last_successful_sync_at,
            last_failed_sync_at=connection.last_failed_sync_at,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )
        self.connection = connection
        supports_catalog = connection.connection_type in {"erpnext", "zoho_inventory"}
        self.supports_preview = supports_catalog
        self.supports_import = supports_catalog
        self.supports_stock_sync = supports_catalog

    def on_test_result(self, *, ok: bool) -> None:
        super().on_test_result(ok=ok)
        now = utc_now()
        if ok:
            self.connection.last_successful_sync_at = now
        else:
            self.connection.last_failed_sync_at = now
        self.connection.status = self.status

    def on_import_success(self) -> None:
        super().on_import_success()
        self.connection.status = self.status
        self.connection.last_successful_sync_at = utc_now()

    def on_stock_sync_success(self) -> None:
        super().on_stock_sync_success()
        self.connection.status = self.status
        self.connection.last_successful_sync_at = utc_now()

    def persist_state(self) -> None:
        db.session.add(self.connection)


class SystemIntegrationAdapter(IntegrationAdapter):
    def __init__(self, *, definition: dict[str, Any], connection_id: int, config: dict[str, Any]) -> None:
        base_url = str(config.get(definition["base_url_config_key"]) or "")
        credentials = {
            field_name: config.get(config_key)
            for field_name, config_key in definition.get("credential_fields", ())
        }
        is_active = bool(base_url) or definition["connection_type"] == "mpesa"
        has_key = any(credentials.get(key) for key in ("consumer_key", "username", "account_sid", "client_id", "organization_id"))
        status = "active" if is_active and (has_key or definition["connection_type"] in {"smtp", "sentry"}) else "error"
        super().__init__(
            connection_id=connection_id,
            name=definition["name"],
            connection_type=definition["connection_type"],
            base_url=base_url,
            auth_type=definition["auth_type"],
            credential_source=definition["credential_source"],
            secret_env_prefix=definition["secret_env_prefix"],
            credentials=credentials,
            credentials_read_only=True,
            status=status,
            is_active=is_active,
        )
        supports_catalog = definition["connection_type"] in {"erpnext", "zoho_inventory"}
        self.supports_preview = supports_catalog
        self.supports_import = supports_catalog
        self.supports_stock_sync = supports_catalog
