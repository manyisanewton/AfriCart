from flask import Blueprint


support_bp = Blueprint("support", __name__, url_prefix="/api/v1/support")


from app.blueprints.support import routes  # noqa: E402,F401
