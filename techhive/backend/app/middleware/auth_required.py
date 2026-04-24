from functools import wraps

from flask import g, request

from app.blueprints.auth.helpers import auth_error
from app.services.auth_token_service import resolve_user_from_token


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header.startswith("Bearer "):
            return auth_error("Authorization header with Bearer token is required.")

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return auth_error("Bearer token is required.")

        user, payload, error = resolve_user_from_token(
            token,
            expected_type="access",
            required_message="Access token is required.",
        )
        if error is not None:
            return auth_error(error.message, error.status_code)

        g.current_user = user
        request.current_user = user
        g.jwt_payload = payload
        return fn(*args, **kwargs)

    return wrapper
