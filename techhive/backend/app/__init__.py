import logging

from flask import Flask, jsonify
from sqlalchemy import text

from app.blueprints.auth import auth_bp
from app.blueprints.admin import admin_bp
from app.blueprints.cart import cart_bp
from app.blueprints.delivery import delivery_bp
from app.blueprints.notifications import notifications_bp
from app.blueprints.orders import orders_bp
from app.blueprints.payments import payments_bp
from app.blueprints.products import products_bp
from app.blueprints.promotions import promotions_bp
from app.blueprints.reviews import reviews_bp
from app.blueprints.vendors import vendors_bp
from app.extensions import db, migrate, swagger
from app import models
from config import get_config


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    configure_logging(app)
    register_extensions(app)
    register_routes(app)
    register_error_handlers(app)

    return app


def configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(logging.INFO)


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    swagger.template = {
        "swagger": "2.0",
        "info": {
            "title": app.config["APP_NAME"],
            "version": app.config["APP_VERSION"],
            "description": "Backend API for the TechHive ecommerce platform.",
        },
        "basePath": "/",
        "schemes": ["http", "https"],
    }
    swagger.init_app(app)


def register_routes(app: Flask) -> None:
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(promotions_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(vendors_bp)

    @app.get("/health")
    def health_check():
        """
        Lightweight health endpoint for uptime checks.
        ---
        tags:
          - System
        responses:
          200:
            description: Service health information.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: healthy
                service:
                  type: string
                  example: TechHive API
                version:
                  type: string
                  example: 0.1.0
        """
        return jsonify(
            {
                "status": "healthy",
                "service": app.config["APP_NAME"],
                "version": app.config["APP_VERSION"],
            }
        )

    @app.get("/ready")
    def readiness_check():
        """
        Readiness endpoint that verifies core dependencies.
        ---
        tags:
          - System
        responses:
          200:
            description: Service is ready to accept traffic.
          503:
            description: Service is not ready.
        """
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - exercised in tests via monkeypatch
            app.logger.exception("Readiness check failed: %s", exc)
            return (
                jsonify(
                    {
                        "status": "not_ready",
                        "service": app.config["APP_NAME"],
                        "checks": {"database": "error"},
                    }
                ),
                503,
            )

        return jsonify(
            {
                "status": "ready",
                "service": app.config["APP_NAME"],
                "checks": {"database": "ok"},
            }
        )

    @app.get("/metrics")
    def metrics():
        """
        Prometheus-compatible metrics endpoint.
        ---
        tags:
          - System
        responses:
          200:
            description: Metrics payload.
        """
        db_ready = 1
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db_ready = 0

        lines = [
            "# HELP techhive_app_info Static application metadata.",
            "# TYPE techhive_app_info gauge",
            f'techhive_app_info{{service="{app.config["APP_NAME"]}",version="{app.config["APP_VERSION"]}"}} 1',
            "# HELP techhive_db_ready Database readiness status.",
            "# TYPE techhive_db_ready gauge",
            f"techhive_db_ready {db_ready}",
        ]
        return app.response_class("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")

    @app.get("/")
    def root():
        return jsonify(
            {
                "message": "Welcome to the TechHive API.",
                "docs_url": "/docs/",
                "health_url": "/health",
                "readiness_url": "/ready",
                "metrics_url": "/metrics",
            }
        )


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def handle_not_found(error):
        return (
            jsonify(
                {
                    "error": {
                        "code": "not_found",
                        "message": "The requested resource was not found.",
                    }
                }
            ),
            404,
        )

    @app.errorhandler(500)
    def handle_server_error(error):
        app.logger.exception("Unhandled server error: %s", error)
        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred.",
                    }
                }
            ),
            500,
        )
