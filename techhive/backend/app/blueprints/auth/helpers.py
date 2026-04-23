from flask import jsonify

from app.models import User
from app.utils.security import (
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
)


def auth_error(message: str, status_code: int = 401):
    return jsonify({"error": {"code": "auth_error", "message": message}}), status_code


def validation_error(errors: dict):
    return jsonify({"error": {"code": "validation_error", "details": errors}}), 400


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "role": user.role.value,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
    }


def auth_response(user: User):
    return jsonify(
        {
            "user": user_to_dict(user),
            "tokens": {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
                "token_type": "Bearer",
            },
            "verification": {
                "email_verification_token": create_email_verification_token(user.id),
            },
        }
    )
