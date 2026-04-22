from functools import wraps

import jwt
from flask import g, request

from app.blueprints.auth.helpers import auth_error
from app.extensions import db
from app.models import User
from app.utils.security import decode_token


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header.startswith("Bearer "):
            return auth_error("Authorization header with Bearer token is required.")

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return auth_error("Bearer token is required.")

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return auth_error("Token has expired.")
        except jwt.InvalidTokenError:
            return auth_error("Token is invalid.")

        if payload.get("type") != "access":
            return auth_error("Access token is required.")

        user = db_lookup_user(payload.get("sub"))
        if user is None or not user.is_active:
            return auth_error("Authenticated user is not available.")

        g.current_user = user
        request.current_user = user
        g.jwt_payload = payload
        return fn(*args, **kwargs)

    return wrapper


def db_lookup_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
