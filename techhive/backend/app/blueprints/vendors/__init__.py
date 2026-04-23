from flask import Blueprint


vendors_bp = Blueprint("vendors", __name__, url_prefix="/api/v1/vendor")


from app.blueprints.vendors import routes  # noqa: E402,F401
from app.blueprints.vendors import kyc  # noqa: E402,F401
