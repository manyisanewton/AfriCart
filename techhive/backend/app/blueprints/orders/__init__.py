from flask import Blueprint


orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


from app.blueprints.orders import routes  # noqa: E402,F401
