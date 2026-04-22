from config import DevelopmentConfig, TestingConfig, get_config


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
    assert response.get_json() == {
        "status": "ready",
        "service": "TechHive API",
        "checks": {"database": "ok"},
    }


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
