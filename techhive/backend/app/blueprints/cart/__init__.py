from flask import Blueprint


cart_bp = Blueprint("cart", __name__, url_prefix="/api/v1")


from app.blueprints.cart import routes  # noqa: E402,F401
