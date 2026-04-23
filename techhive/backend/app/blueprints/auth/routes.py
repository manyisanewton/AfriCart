import jwt
from flask import g, request

from app.blueprints.auth import auth_bp
from app.blueprints.auth.helpers import auth_error, auth_response, user_to_dict, validation_error
from app.blueprints.auth.schemas import (
    validate_change_password_payload,
    validate_email_payload,
    validate_login_payload,
    validate_password_reset_payload,
    validate_refresh_payload,
    validate_registration_payload,
    validate_token_payload,
)
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.middleware.rate_limiter import rate_limit
from app.models import User
from app.services.email_service import send_email
from app.utils.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)


@auth_bp.post("/register")
@rate_limit("auth_register", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
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
@rate_limit("auth_login", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
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
@rate_limit("auth_refresh", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
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


@auth_bp.post("/logout")
@rate_limit("auth_logout", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
def logout():
    """
    Perform a stateless logout by validating the submitted refresh token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Logout acknowledged.
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

    return {"message": "Logout successful. Discard the current tokens on the client."}


@auth_bp.post("/change-password")
@auth_required
def change_password():
    """
    Change the authenticated user's password.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Password changed.
    """
    payload = validate_change_password_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    if not verify_password(g.current_user.password_hash, payload["current_password"]):
        return auth_error("Current password is incorrect.", 400)

    g.current_user.password_hash = hash_password(payload["new_password"])
    db.session.commit()
    return {"message": "Password changed successfully."}


@auth_bp.post("/forgot-password")
@rate_limit("auth_forgot_password", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
def forgot_password():
    """
    Request a password reset token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Reset flow initiated.
    """
    payload = validate_email_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = User.query.filter_by(email=payload["email"]).first()
    if user is None:
        return {"message": "If the account exists, a password reset email has been prepared."}

    reset_token = create_password_reset_token(user.id)
    email_job = send_email(
        to_email=user.email,
        subject="Reset your TechHive password",
        template="password_reset",
        context={"reset_token": reset_token, "email": user.email},
    )
    return {
        "message": "If the account exists, a password reset email has been prepared.",
        "reset_token": reset_token,
        "delivery": email_job,
    }


@auth_bp.post("/reset-password")
@rate_limit("auth_reset_password", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
def reset_password():
    """
    Reset a password using a password reset token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Password reset successfully.
    """
    payload = validate_password_reset_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    try:
        token_payload = decode_token(payload["token"])
    except jwt.ExpiredSignatureError:
        return auth_error("Password reset token has expired.")
    except jwt.InvalidTokenError:
        return auth_error("Password reset token is invalid.")

    if token_payload.get("type") != "password_reset":
        return auth_error("Password reset token is required.")

    user = db.session.get(User, int(token_payload["sub"]))
    if user is None:
        return auth_error("Authenticated user is not available.", 404)

    user.password_hash = hash_password(payload["new_password"])
    db.session.commit()
    return {"message": "Password reset successfully."}


@auth_bp.post("/verify-email")
@rate_limit("auth_verify_email", "RATE_LIMIT_AUTH_MAX_REQUESTS", "RATE_LIMIT_AUTH_WINDOW_SECONDS")
def verify_email():
    """
    Verify a user's email using a verification token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Email verified.
    """
    payload = validate_token_payload(request.get_json(silent=True), field_name="verification_token")
    if "errors" in payload:
        return validation_error(payload["errors"])

    try:
        token_payload = decode_token(payload["verification_token"])
    except jwt.ExpiredSignatureError:
        return auth_error("Email verification token has expired.")
    except jwt.InvalidTokenError:
        return auth_error("Email verification token is invalid.")

    if token_payload.get("type") != "email_verification":
        return auth_error("Email verification token is required.")

    user = db.session.get(User, int(token_payload["sub"]))
    if user is None:
        return auth_error("Authenticated user is not available.", 404)

    user.email_verified = True
    db.session.commit()
    return {"message": "Email verified successfully."}


@auth_bp.post("/resend-verification")
@auth_required
def resend_verification():
    """
    Generate a new email verification token for the authenticated user.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Verification email prepared.
    """
    verification_token = create_email_verification_token(g.current_user.id)
    email_job = send_email(
        to_email=g.current_user.email,
        subject="Verify your TechHive email",
        template="email_verification",
        context={"verification_token": verification_token, "email": g.current_user.email},
    )
    return {
        "message": "Verification email prepared successfully.",
        "verification_token": verification_token,
        "delivery": email_job,
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
