from flask import Flask, request

from app.utils.validators import parse_allowed_origins


def register_cors(app: Flask) -> None:
    @app.after_request
    def add_cors_headers(response):
        allowed_origins = app.config.get("CORS_ALLOWED_ORIGINS", "*")
        request_origin = request.headers.get("Origin")

        if allowed_origins == "*":
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif request_origin:
            allowed = parse_allowed_origins(allowed_origins)
            if request_origin in allowed:
                response.headers["Access-Control-Allow-Origin"] = request_origin

        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
        return response
