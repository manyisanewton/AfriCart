from __future__ import annotations

from flask import jsonify, request


def error_response(*, code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message}}), status_code


def not_found_response(message: str):
    return error_response(code="not_found", message=message, status_code=404)


def validation_error_response(errors: dict):
    return jsonify({"error": {"code": "validation_error", "details": errors}}), 400


def get_json_payload() -> dict:
    return request.get_json(silent=True) or {}


def parse_positive_int(value, *, field_name: str) -> tuple[int | None, dict[str, str] | None]:
    try:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return None, {field_name: f"{field_name} must be a positive integer."}
    return parsed, None
