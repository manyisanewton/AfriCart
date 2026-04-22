from flask import Blueprint


promotions_bp = Blueprint("promotions", __name__, url_prefix="/api/v1")


from app.blueprints.promotions import routes  # noqa: E402,F401
