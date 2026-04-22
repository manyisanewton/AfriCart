import sys
from types import ModuleType, SimpleNamespace

from app import create_app
from app.services import error_monitoring_service


def test_error_monitoring_is_disabled_without_dsn():
    app = create_app("testing")

    assert error_monitoring_service.initialize_error_monitoring(app) is False


def test_error_monitoring_initializes_when_sdk_is_available(monkeypatch):
    calls = []

    fake_sentry_sdk = ModuleType("sentry_sdk")
    fake_sentry_sdk.init = lambda **kwargs: calls.append(kwargs)
    fake_flask_module = ModuleType("sentry_sdk.integrations.flask")
    fake_flask_module.FlaskIntegration = lambda: SimpleNamespace(name="flask")

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry_sdk)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.flask", fake_flask_module)

    app = create_app("testing")
    app.config["SENTRY_DSN"] = "https://example@sentry.io/123"
    app.config["SENTRY_ENVIRONMENT"] = "testing"
    app.config["SENTRY_TRACES_SAMPLE_RATE"] = 0.25

    initialized = error_monitoring_service.initialize_error_monitoring(app)

    assert initialized is True
    assert len(calls) == 1
    assert calls[0]["dsn"] == "https://example@sentry.io/123"
    assert calls[0]["environment"] == "testing"
    assert calls[0]["traces_sample_rate"] == 0.25
