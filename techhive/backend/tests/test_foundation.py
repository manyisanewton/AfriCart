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
