from flask import Blueprint


notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


from app.blueprints.notifications import routes  # noqa: E402,F401
