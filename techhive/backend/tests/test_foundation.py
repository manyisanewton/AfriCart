import importlib

import config as config_module
import pytest
from config import DevelopmentConfig, TestingConfig, get_config
from app import create_app
from app.services.runtime_config_service import (
    RuntimeConfigurationError,
    collect_runtime_config_report,
)


def test_create_app_uses_testing_config(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == TestingConfig.SQLALCHEMY_DATABASE_URI


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "healthy",
        "service": "TechHive API",
        "version": "0.1.0",
    }


def test_root_endpoint_exposes_service_links(client):
    response = client.get("/")

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["message"] == "Welcome to the TechHive API."
    assert payload["docs_url"] == "/docs/"
    assert payload["health_url"] == "/health"
    assert payload["readiness_url"] == "/ready"
    assert payload["metrics_url"] == "/metrics"


def test_readiness_endpoint(client):
    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["service"] == "TechHive API"
    assert payload["checks"]["database"] == "ok"
    assert "runtime" in payload["checks"]
    assert "valid" in payload["checks"]["runtime"]


def test_metrics_endpoint(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.get_data(as_text=True)
    assert "techhive_app_info" in payload
    assert "techhive_db_ready 1" in payload


def test_security_headers_are_present(client):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_default_cors_headers_are_present(client):
    response = client.get("/", headers={"Origin": "https://example.com"})

    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


def test_request_id_header_is_present(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_missing_route_returns_standard_error_shape(client):
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": {
            "code": "not_found",
            "message": "The requested resource was not found.",
        }
    }


def test_get_config_defaults_to_development():
    assert get_config("development") is DevelopmentConfig


def test_get_config_returns_testing_class():
    assert get_config("testing") is TestingConfig


def test_runtime_defaults_are_available_on_app_config(app):
    assert app.config["HOST"] == "0.0.0.0"
    assert app.config["PORT"] == 5000
    assert app.config["GUNICORN_WORKERS"] == 2


def test_worker_health_includes_runtime_config(client):
    response = client.get("/workers/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert "runtime_config" in payload["task_queue"]
    assert "valid" in payload["task_queue"]["runtime_config"]


def test_dotenv_values_are_loaded(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("HOST=127.0.0.1\nPORT=5050\n", encoding="utf-8")
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    config_module.load_environment(tmp_path)

    assert config_module.os.getenv("HOST") == "127.0.0.1"
    assert config_module.os.getenv("PORT") == "5050"


def test_mail_and_twilio_aliases_are_supported(monkeypatch):
    monkeypatch.setenv("MAIL_SERVER", "smtp.example.com")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USE_TLS", "true")
    monkeypatch.setenv("MAIL_USERNAME", "mailer@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "secret")
    monkeypatch.setenv("MAIL_DEFAULT_SENDER", "Deliveroo <mailer@example.com>")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "(814) 399-8680")
    reloaded = importlib.reload(config_module)

    assert reloaded.Config.SMTP_HOST == "smtp.example.com"
    assert reloaded.Config.SMTP_PORT == 2525
    assert reloaded.Config.SMTP_USE_TLS is True
    assert reloaded.Config.SMTP_USERNAME == "mailer@example.com"
    assert reloaded.Config.SMTP_PASSWORD == "secret"
    assert reloaded.Config.SMTP_FROM_EMAIL == "mailer@example.com"
    assert reloaded.Config.SMTP_FROM_NAME == "Deliveroo"
    assert reloaded.Config.TWILIO_FROM_NUMBER == "(814) 399-8680"

    for key in (
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_USE_TLS",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_DEFAULT_SENDER",
        "TWILIO_PHONE_NUMBER",
    ):
        monkeypatch.delenv(key, raising=False)
    importlib.reload(config_module)


def test_payment_method_csv_config_is_supported(monkeypatch):
    monkeypatch.setenv("PAYMENT_ENABLED_METHODS", "mpesa, manual ,cash_on_delivery")
    monkeypatch.setenv("PAYMENT_PRIMARY_METHOD", "mpesa")
    reloaded = importlib.reload(config_module)

    assert reloaded.Config.PAYMENT_ENABLED_METHODS == (
        "mpesa",
        "manual",
        "cash_on_delivery",
    )
    assert reloaded.Config.PAYMENT_PRIMARY_METHOD == "mpesa"

    monkeypatch.delenv("PAYMENT_ENABLED_METHODS", raising=False)
    monkeypatch.delenv("PAYMENT_PRIMARY_METHOD", raising=False)
    importlib.reload(config_module)


def test_runtime_config_report_collects_development_warnings():
    app = create_app("testing")
    app.config["TESTING"] = False
    app.config["DEBUG"] = True
    app.config["SECRET_KEY"] = "dev-secret-key"
    app.config["PAYMENTS_ALLOW_SIMULATION"] = True
    app.config["MPESA_ALLOW_UNSIGNED_CALLBACKS"] = True

    report = collect_runtime_config_report(app)

    assert report.is_valid is True
    assert any("SECRET_KEY" in warning for warning in report.warnings)
    assert any("PAYMENTS_ALLOW_SIMULATION" in warning for warning in report.warnings)


def test_runtime_config_warns_when_narrowed_to_mpesa_only():
    app = create_app("testing")
    app.config["TESTING"] = False
    app.config["DEBUG"] = True
    app.config["PAYMENT_ENABLED_METHODS"] = ("mpesa",)
    app.config["PAYMENT_PRIMARY_METHOD"] = "mpesa"

    report = collect_runtime_config_report(app)

    assert report.is_valid is True
    assert any("M-Pesa only" in warning for warning in report.warnings)


def test_production_runtime_config_rejects_unsafe_defaults(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/prod.db")
    monkeypatch.setenv("PAYMENT_CALLBACK_BASE_URL", "http://example.com/callback")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("PAYMENTS_ALLOW_SIMULATION", "true")
    monkeypatch.setenv("MPESA_ALLOW_UNSIGNED_CALLBACKS", "true")
    reloaded = importlib.reload(config_module)

    with pytest.raises(RuntimeConfigurationError):
        create_app("production")

    for key in (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
        "PAYMENT_CALLBACK_BASE_URL",
        "CORS_ALLOWED_ORIGINS",
        "PAYMENTS_ALLOW_SIMULATION",
        "MPESA_ALLOW_UNSIGNED_CALLBACKS",
    ):
        monkeypatch.delenv(key, raising=False)
    importlib.reload(config_module)
