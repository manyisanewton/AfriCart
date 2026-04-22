from app.extensions import db
from app.models import User
from app.utils.security import hash_password


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
