from flask import g, jsonify, request

from app.blueprints.delivery import delivery_bp
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.delivery.tracking import resolve_delivery_zone
from app.extensions import db
from app.middleware.role_required import role_required
from app.models import DeliveryAgent, DeliveryZone, Order, UserRole


def serialize_zone(zone: DeliveryZone) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "city": zone.city,
        "fee": zone.fee_amount,
        "estimated_days_min": zone.estimated_days_min,
        "estimated_days_max": zone.estimated_days_max,
        "is_active": zone.is_active,
    }


@delivery_bp.get("/zones")
def list_delivery_zones():
    """
    List active delivery zones.
    ---
    tags:
      - Delivery
    responses:
      200:
        description: Delivery zones.
    """
    zones = DeliveryZone.query.filter_by(is_active=True).order_by(DeliveryZone.city.asc()).all()
    return jsonify({"items": [serialize_zone(zone) for zone in zones]})


@delivery_bp.get("/estimate")
def estimate_delivery():
    """
    Estimate delivery fee by city.
    ---
    tags:
      - Delivery
    responses:
      200:
        description: Delivery estimate.
      404:
        description: Delivery zone not found.
    """
    city = request.args.get("city", type=str)
    zone = resolve_delivery_zone(city)
    if zone is None:
        return jsonify({"error": {"code": "not_found", "message": "Delivery zone not found."}}), 404
    return jsonify({"item": serialize_zone(zone)})


@delivery_bp.get("/track/<string:tracking_token>")
def track_order(tracking_token: str):
    """
    Track an order by its public tracking token.
    ---
    tags:
      - Delivery
    responses:
      200:
        description: Tracking details.
      404:
        description: Order not found.
    """
    order = Order.query.filter_by(tracking_token=tracking_token).first()
    if order is None:
        return jsonify({"error": {"code": "not_found", "message": "Order not found."}}), 404
    return jsonify({"item": serialize_order(order, include_items=True)})


@delivery_bp.post("/orders/<int:order_id>/assign-agent")
@role_required(UserRole.ADMIN.value)
def assign_delivery_agent(order_id: int):
    """
    Assign a delivery agent to an order.
    ---
    tags:
      - Delivery
    responses:
      200:
        description: Delivery agent assigned.
    """
    payload = request.get_json(silent=True) or {}
    try:
        delivery_agent_id = int(payload.get("delivery_agent_id"))
    except (TypeError, ValueError):
        return jsonify({"error": {"code": "validation_error", "details": {"delivery_agent_id": "delivery_agent_id must be a positive integer."}}}), 400
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({"error": {"code": "not_found", "message": "Order not found."}}), 404
    agent = db.session.get(DeliveryAgent, delivery_agent_id)
    if agent is None or not agent.is_active:
        return jsonify({"error": {"code": "validation_error", "details": {"delivery_agent_id": "Selected delivery agent was not found."}}}), 400
    order.delivery_agent_id = agent.id
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})


@delivery_bp.post("/orders/<int:order_id>/status")
@role_required(UserRole.DELIVERY_AGENT.value)
def update_delivery_status(order_id: int):
    """
    Update delivery status for an assigned order.
    ---
    tags:
      - Delivery
    responses:
      200:
        description: Delivery status updated.
    """
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("delivery_status", "")).strip().lower()
    allowed = {"assigned", "in_transit", "delivered", "failed_attempt"}
    if status not in allowed:
        return jsonify({"error": {"code": "validation_error", "details": {"delivery_status": "delivery_status must be one of assigned, in_transit, delivered, failed_attempt."}}}), 400

    agent = g.current_user.delivery_agent_profile
    if agent is None:
        return jsonify({"error": {"code": "delivery_agent_profile_missing", "message": "Delivery agent profile is required for this action."}}), 403

    order = Order.query.filter_by(id=order_id, delivery_agent_id=agent.id).first()
    if order is None:
        return jsonify({"error": {"code": "not_found", "message": "Order not found."}}), 404

    order.delivery_status = status
    if status == "delivered":
        order.status = order.status.__class__.DELIVERED
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})
