from flask import jsonify

from app.blueprints.admin import admin_bp
from app.middleware.role_required import role_required
from app.models import UserRole
from app.services.analytics_service import admin_summary, admin_top_products


@admin_bp.get("/analytics/summary")
@role_required(UserRole.ADMIN.value)
def get_admin_summary():
    """
    Get top-level admin analytics summary.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Admin analytics summary.
    """
    return jsonify({"item": admin_summary()})


@admin_bp.get("/analytics/top-products")
@role_required(UserRole.ADMIN.value)
def get_admin_top_products():
    """
    Get top-selling products across the marketplace.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Top products list.
    """
    return jsonify({"items": admin_top_products()})
