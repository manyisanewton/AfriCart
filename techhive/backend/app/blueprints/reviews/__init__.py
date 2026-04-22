from flask import Blueprint


reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/v1")


from app.blueprints.reviews import routes  # noqa: E402,F401
