from flask import Blueprint


addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/v1/addresses")


from app.blueprints.addresses import routes  # noqa: E402,F401
