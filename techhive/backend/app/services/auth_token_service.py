from __future__ import annotations

from dataclasses import dataclass

import jwt

from app.extensions import db
from app.models import User
from app.utils.security import decode_token


@dataclass
class TokenError:
    message: str
    status_code: int = 401


def decode_typed_token(token: str, *, expected_type: str, required_message: str) -> tuple[dict | None, TokenError | None]:
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        label = expected_type.replace("_", " ")
        return None, TokenError(f"{label.capitalize()} token has expired.")
    except jwt.InvalidTokenError:
        label = expected_type.replace("_", " ")
        return None, TokenError(f"{label.capitalize()} token is invalid.")

    if payload.get("type") != expected_type:
        return None, TokenError(required_message)
    return payload, None


def resolve_user_from_token(
    token: str,
    *,
    expected_type: str,
    required_message: str,
    unavailable_message: str = "Authenticated user is not available.",
    unavailable_status_code: int = 401,
) -> tuple[User | None, dict | None, TokenError | None]:
    payload, token_error = decode_typed_token(
        token,
        expected_type=expected_type,
        required_message=required_message,
    )
    if token_error is not None:
        return None, None, token_error

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None, payload, TokenError(unavailable_message, unavailable_status_code)

    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return None, payload, TokenError(unavailable_message, unavailable_status_code)
    return user, payload, None
