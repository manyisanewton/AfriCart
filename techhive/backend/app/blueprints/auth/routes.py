import jwt
from flask import g, request

from app.blueprints.auth import auth_bp
from app.blueprints.auth.helpers import auth_error, auth_response, user_to_dict, validation_error
from app.blueprints.auth.schemas import (
    validate_login_payload,
    validate_refresh_payload,
    validate_registration_payload,
)
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import User
from app.utils.security import create_access_token, decode_token, hash_password, verify_password


@auth_bp.post("/register")
def register():
    """
    Register a new customer account.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password, first_name, last_name]
          properties:
            email:
              type: string
            password:
              type: string
            first_name:
              type: string
            last_name:
              type: string
            phone_number:
              type: string
    responses:
      201:
        description: Account created successfully.
    """
    payload = validate_registration_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    email = payload["email"]
    phone_number = payload["phone_number"]

    if User.query.filter_by(email=email).first():
        return validation_error({"email": "An account with that email already exists."})

    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return validation_error(
            {"phone_number": "An account with that phone number already exists."}
        )

    user = User(
        email=email,
        password_hash=hash_password(payload["password"]),
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        phone_number=phone_number,
    )
    db.session.add(user)
    db.session.commit()

    return auth_response(user), 201


@auth_bp.post("/login")
def login():
    """
    Log in with email and password.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Login successful.
    """
    payload = validate_login_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = User.query.filter_by(email=payload["email"]).first()
    if user is None or not verify_password(user.password_hash, payload["password"]):
        return auth_error("Invalid email or password.")

    if not user.is_active:
        return auth_error("This account is inactive.", 403)

    return auth_response(user)


@auth_bp.post("/refresh")
def refresh():
    """
    Refresh an access token using a refresh token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Access token refreshed successfully.
    """
    payload = validate_refresh_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    try:
        token_payload = decode_token(payload["refresh_token"])
    except jwt.ExpiredSignatureError:
        return auth_error("Refresh token has expired.")
    except jwt.InvalidTokenError:
        return auth_error("Refresh token is invalid.")

    if token_payload.get("type") != "refresh":
        return auth_error("Refresh token is required.")

    user = db.session.get(User, int(token_payload["sub"]))
    if user is None or not user.is_active:
        return auth_error("Authenticated user is not available.")

    return {
        "access_token": create_access_token(user.id),
        "token_type": "Bearer",
    }


@auth_bp.get("/me")
@auth_required
def get_current_user():
    """
    Get the currently authenticated user.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Current user profile.
    """
    return {"user": user_to_dict(g.current_user)}
