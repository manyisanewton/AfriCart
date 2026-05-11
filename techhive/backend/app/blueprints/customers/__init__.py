from flask import Blueprint


customers_bp = Blueprint("customers", __name__, url_prefix="/api/v1/customer")


from app.blueprints.customers import routes  # noqa: E402,F401
