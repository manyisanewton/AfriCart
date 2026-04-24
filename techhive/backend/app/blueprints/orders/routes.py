from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.orders import orders_bp
from app.blueprints.orders.helpers import serialize_order, serialize_refund
from app.blueprints.orders.schemas import validate_create_order_payload, validate_refund_request_payload
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import (
    Order,
)
from app.services.order_service import (
    ServiceError,
    cancel_order_for_user,
    create_order_from_cart,
    get_user_order,
    request_refund_for_order,
)
from app.utils.api import get_json_payload, not_found_response


def _validation_or_not_found(error: ServiceError):
    if error.status_code == 404:
        return not_found_response("Order not found.")
    return validation_error(error.details)


@orders_bp.get("")
@auth_required
def list_orders():
    """
    List the authenticated user's orders.
    ---
    tags:
      - Orders
    responses:
      200:
        description: Current user's orders.
    """
    orders = (
        Order.query.filter_by(user_id=g.current_user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_order(order) for order in orders]})


@orders_bp.post("")
@auth_required
def create_order():
    """
    Create an order from the authenticated user's cart.
    ---
    tags:
      - Orders
    responses:
      201:
        description: Order created successfully.
    """
    payload = validate_create_order_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    order, error = create_order_from_cart(
        user_id=g.current_user.id,
        address_id=payload["address_id"],
        notes=payload["notes"],
        promo_code_value=payload["promo_code"],
    )
    if error:
        return _validation_or_not_found(error)

    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)}), 201


@orders_bp.get("/<int:order_id>")
@auth_required
def get_order(order_id: int):
    """
    Get a specific authenticated user's order.
    ---
    tags:
      - Orders
    responses:
      200:
        description: Order details.
      404:
        description: Order not found.
    """
    order = get_user_order(user_id=g.current_user.id, order_id=order_id)
    if order is None:
        return not_found_response("Order not found.")
    return jsonify({"item": serialize_order(order, include_items=True)})


@orders_bp.post("/<int:order_id>/cancel")
@auth_required
def cancel_order(order_id: int):
    """
    Cancel an order if it is still pending.
    ---
    tags:
      - Orders
    responses:
      200:
        description: Order cancelled.
      400:
        description: Order cannot be cancelled.
    """
    order, error = cancel_order_for_user(user_id=g.current_user.id, order_id=order_id)
    if error:
        if error.status_code == 404:
            return not_found_response("Order not found.")
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": error.details["order"],
                    }
                }
            ),
            error.status_code,
        )

    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})


@orders_bp.post("/<int:order_id>/refund-request")
@auth_required
def request_refund(order_id: int):
    """
    Request a refund for a paid order.
    ---
    tags:
      - Orders
    responses:
      201:
        description: Refund requested.
      400:
        description: Refund request rejected.
    """
    payload = validate_refund_request_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    refund, error = request_refund_for_order(
        user_id=g.current_user.id,
        order_id=order_id,
        reason=payload["reason"],
    )
    if error:
        return _validation_or_not_found(error)

    db.session.commit()
    return jsonify({"item": serialize_refund(refund)}), 201
