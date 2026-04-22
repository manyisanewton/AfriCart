from functools import wraps

from flask import g

from app.blueprints.auth.helpers import auth_error
from app.middleware.auth_required import auth_required


def role_required(*allowed_roles):
    def decorator(fn):
        @auth_required
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.current_user.role.value not in allowed_roles:
                return auth_error("You do not have permission to access this resource.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
