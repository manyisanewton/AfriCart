from __future__ import annotations

from dataclasses import dataclass

from app.models import User


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def update_user_profile(
    *,
    user: User,
    email: str | None,
    first_name: str | None,
    last_name: str | None,
    phone_number: str | None,
) -> tuple[User | None, ServiceError | None]:
    changed_email = False

    if email is not None and email != user.email:
        existing_email = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_email is not None:
            return None, ServiceError({"email": "An account with that email already exists."})
        user.email = email
        user.email_verified = False
        changed_email = True

    if phone_number != user.phone_number:
        if phone_number:
            existing_phone = User.query.filter(
                User.phone_number == phone_number,
                User.id != user.id,
            ).first()
            if existing_phone is not None:
                return None, ServiceError(
                    {"phone_number": "An account with that phone number already exists."}
                )
        user.phone_number = phone_number

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name

    setattr(user, "_email_changed_for_response", changed_email)
    return user, None
