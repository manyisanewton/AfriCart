from flask import Blueprint


checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/v1/checkout")


from app.blueprints.checkout import routes  # noqa: E402,F401
