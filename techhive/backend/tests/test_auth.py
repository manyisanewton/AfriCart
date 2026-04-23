from app.extensions import db
from app.models import User
from app.utils.security import create_email_verification_token, create_password_reset_token, hash_password


def create_existing_user():
    user = User(
        email="existing@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Existing",
        last_name="User",
        phone_number="+254700123456",
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_register_creates_user_and_returns_tokens(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "+254700888111",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["email"] == "newuser@example.com"
    assert payload["tokens"]["access_token"]
    assert payload["tokens"]["refresh_token"]


def test_register_rejects_duplicate_email(client):
    create_existing_user()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "password": "SecurePass123",
            "first_name": "Another",
            "last_name": "User",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["email"] == (
        "An account with that email already exists."
    )


def test_login_returns_tokens_for_valid_credentials(client):
    create_existing_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "SecurePass123"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["tokens"]["access_token"]
    assert payload["tokens"]["refresh_token"]
    assert payload["user"]["full_name"] == "Existing User"


def test_login_rejects_invalid_credentials(client):
    create_existing_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Invalid email or password."


def test_me_requires_valid_access_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert "Bearer token" in response.get_json()["error"]["message"]


def test_me_returns_authenticated_user(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authuser@example.com",
            "password": "SecurePass123",
            "first_name": "Auth",
            "last_name": "User",
        },
    )
    access_token = register_response.get_json()["tokens"]["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "authuser@example.com"


def test_refresh_returns_new_access_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "SecurePass123",
            "first_name": "Refresh",
            "last_name": "User",
        },
    )
    refresh_token = register_response.get_json()["tokens"]["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["access_token"]
    assert payload["token_type"] == "Bearer"


def test_login_rate_limit_returns_429_after_threshold(client, app):
    app.config["RATE_LIMIT_AUTH_MAX_REQUESTS"] = 2
    create_existing_user()

    response_one = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "wrong-password"},
    )
    response_two = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "wrong-password"},
    )
    response_three = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "wrong-password"},
    )

    assert response_one.status_code == 401
    assert response_two.status_code == 401
    assert response_three.status_code == 429
    assert response_three.get_json()["error"]["code"] == "rate_limit_exceeded"


def test_logout_acknowledges_valid_refresh_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "SecurePass123",
            "first_name": "Logout",
            "last_name": "User",
        },
    )
    refresh_token = register_response.get_json()["tokens"]["refresh_token"]

    response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert "Logout successful" in response.get_json()["message"]


def test_change_password_updates_user_password(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "change@example.com",
            "password": "SecurePass123",
            "first_name": "Change",
            "last_name": "Password",
        },
    )
    access_token = register_response.get_json()["tokens"]["access_token"]

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "SecurePass123", "new_password": "NewSecure456"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "change@example.com", "password": "NewSecure456"},
    )
    assert login_response.status_code == 200


def test_forgot_password_returns_reset_token_for_existing_user(client):
    create_existing_user()

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "existing@example.com"},
    )

    assert response.status_code == 200
    assert response.get_json()["reset_token"]
    assert response.get_json()["delivery"]["template"] == "password_reset"


def test_reset_password_updates_credentials(client):
    user = create_existing_user()
    with client.application.app_context():
        token = create_password_reset_token(user.id)

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "ResetPass456"},
    )

    assert response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "ResetPass456"},
    )
    assert login_response.status_code == 200


def test_verify_email_marks_user_as_verified(client):
    user = create_existing_user()
    with client.application.app_context():
        token = create_email_verification_token(user.id)

    response = client.post(
        "/api/v1/auth/verify-email",
        json={"verification_token": token},
    )

    assert response.status_code == 200
    refreshed_user = db.session.get(User, user.id)
    assert refreshed_user.email_verified is True


def test_resend_verification_returns_new_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verifyme@example.com",
            "password": "SecurePass123",
            "first_name": "Verify",
            "last_name": "Again",
        },
    )
    access_token = register_response.get_json()["tokens"]["access_token"]

    response = client.post(
        "/api/v1/auth/resend-verification",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["verification_token"]
    assert response.get_json()["delivery"]["template"] == "email_verification"
