from __future__ import annotations

from flask import current_app
from sqlalchemy import inspect

from app.extensions import db
from app.models import User, UserRole
from app.utils.security import hash_password


def ensure_bootstrap_admin() -> None:
    if not current_app.config.get("BOOTSTRAP_ADMIN_ENABLED"):
        return

    inspector = inspect(db.engine)
    if not inspector.has_table("users"):
        current_app.logger.info("Skipping bootstrap admin setup because users table does not exist yet.")
        return

    email = str(current_app.config.get("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
    password = str(current_app.config.get("BOOTSTRAP_ADMIN_PASSWORD") or "")

    if not email or not password:
        current_app.logger.warning(
            "BOOTSTRAP_ADMIN_ENABLED is true but BOOTSTRAP_ADMIN_EMAIL or BOOTSTRAP_ADMIN_PASSWORD is missing."
        )
        return

    user = User.query.filter_by(email=email).first()
    password_changed = False

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=str(current_app.config.get("BOOTSTRAP_ADMIN_FIRST_NAME") or "Global").strip(),
            last_name=str(current_app.config.get("BOOTSTRAP_ADMIN_LAST_NAME") or "Admin").strip(),
            phone_number=str(current_app.config.get("BOOTSTRAP_ADMIN_PHONE_NUMBER") or "").strip() or None,
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=bool(current_app.config.get("BOOTSTRAP_ADMIN_EMAIL_VERIFIED", True)),
            must_change_password=False,
        )
        db.session.add(user)
        password_changed = True
        action = "created"
    else:
        action = "updated"
        user.role = UserRole.ADMIN
        user.is_active = True
        if current_app.config.get("BOOTSTRAP_ADMIN_EMAIL_VERIFIED", True):
            user.email_verified = True
        first_name = str(current_app.config.get("BOOTSTRAP_ADMIN_FIRST_NAME") or "").strip()
        last_name = str(current_app.config.get("BOOTSTRAP_ADMIN_LAST_NAME") or "").strip()
        phone_number = str(current_app.config.get("BOOTSTRAP_ADMIN_PHONE_NUMBER") or "").strip() or None
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if phone_number:
            user.phone_number = phone_number
        if current_app.config.get("BOOTSTRAP_ADMIN_RESET_PASSWORD_ON_STARTUP"):
            user.password_hash = hash_password(password)
            password_changed = True
        user.must_change_password = False

    db.session.commit()
    current_app.logger.info(
        "Bootstrap admin %s for %s%s",
        action,
        email,
        " (password refreshed)" if password_changed and action == "updated" else "",
    )
