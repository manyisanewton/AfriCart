from flask import g, jsonify

from app.blueprints.customers import customers_bp
from app.middleware.role_required import role_required
from app.models import UserRole
from app.services.customer_dashboard_service import build_customer_dashboard


@customers_bp.get("/dashboard")
@role_required(UserRole.CUSTOMER.value)
def get_customer_dashboard():
    """
    Get the authenticated customer's dashboard summary.
    ---
    tags:
      - Customers
    responses:
      200:
        description: Customer dashboard summary.
    """
    return jsonify({"item": build_customer_dashboard(g.current_user)})
