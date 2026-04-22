from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def _token_payload(user_id: int, token_type: str, expires_delta) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }


def create_access_token(user_id: int) -> str:
    expires = timedelta(
        minutes=current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"]
    )
    payload = _token_payload(user_id, "access", expires)
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    expires = timedelta(days=current_app.config["JWT_REFRESH_TOKEN_EXPIRES_DAYS"])
    payload = _token_payload(user_id, "refresh", expires)
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=["HS256"],
    )
