from flask import Blueprint


payments_bp = Blueprint("payments", __name__, url_prefix="/api/v1/payments")


from app.blueprints.payments import routes  # noqa: E402,F401
from app.blueprints.payments import webhooks  # noqa: E402,F401
