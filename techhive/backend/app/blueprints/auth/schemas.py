import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_registration_payload(payload: dict | None) -> dict:
    data = payload or {}
    required_fields = [
        "email",
        "password",
        "first_name",
        "last_name",
    ]
    errors = {}

    for field in required_fields:
        if not str(data.get(field, "")).strip():
            errors[field] = f"{field} is required."

    email = str(data.get("email", "")).strip().lower()
    if email and not EMAIL_PATTERN.match(email):
        errors["email"] = "email must be a valid email address."

    password = str(data.get("password", ""))
    if password and len(password) < 8:
        errors["password"] = "password must be at least 8 characters long."

    if errors:
        return {"errors": errors}

    return {
        "email": email,
        "password": password,
        "first_name": str(data["first_name"]).strip(),
        "last_name": str(data["last_name"]).strip(),
        "phone_number": str(data.get("phone_number") or "").strip() or None,
    }


def validate_login_payload(payload: dict | None) -> dict:
    data = payload or {}
    errors = {}

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email:
        errors["email"] = "email is required."
    elif not EMAIL_PATTERN.match(email):
        errors["email"] = "email must be a valid email address."

    if not password:
        errors["password"] = "password is required."

    if errors:
        return {"errors": errors}

    return {"email": email, "password": password}


def validate_refresh_payload(payload: dict | None) -> dict:
    data = payload or {}
    token = str(data.get("refresh_token", "")).strip()
    if not token:
        return {"errors": {"refresh_token": "refresh_token is required."}}
    return {"refresh_token": token}
