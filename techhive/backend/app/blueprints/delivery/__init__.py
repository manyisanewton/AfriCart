from flask import Blueprint


delivery_bp = Blueprint("delivery", __name__, url_prefix="/api/v1/delivery")


from app.blueprints.delivery import routes  # noqa: E402,F401
