from flask import Blueprint


admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


from app.blueprints.admin import analytics  # noqa: E402,F401
from app.blueprints.admin import routes  # noqa: E402,F401
