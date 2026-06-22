from flask import current_app, g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.checkout import checkout_bp
from app.blueprints.checkout.schemas import (
    validate_checkout_order_payload,
    validate_checkout_payment_payload,
    validate_checkout_quote_payload,
)
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.payments.helpers import serialize_payment
from app.extensions import db
from app.services.audit_service import log_request_audit_event
from app.services.auth_token_service import resolve_user_from_token
from app.services.order_service import (
    ServiceError,
    create_checkout_order,
    get_checkout_quote,
    get_order_for_tracking_token,
)
from app.services.payment_service import create_payment_for_order
from app.utils.api import get_json_payload, not_found_response


def _resolve_optional_user():
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None

    user, payload, error = resolve_user_from_token(
        token,
        expected_type="access",
        required_message="Access token is required.",
    )
    if error is not None:
        return None

    g.current_user = user
    g.jwt_payload = payload
    return user


def _service_error_response(error: ServiceError):
    if error.status_code == 404:
        return not_found_response(next(iter(error.details.values()), "Not found."))
    return validation_error(error.details)


@checkout_bp.post("/quote")
def create_checkout_quote():
    payload = validate_checkout_quote_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    quote, error = get_checkout_quote(
        address=payload["address"],
        items=payload["items"],
        delivery_location=payload["delivery_location"],
        promo_code_value=payload["promo_code"],
    )
    if error:
        return _service_error_response(error)
    return jsonify({"item": quote})


@checkout_bp.post("/orders")
def create_checkout_order_route():
    payload = validate_checkout_order_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = _resolve_optional_user()
    order, error = create_checkout_order(
        user=user,
        customer=payload["customer"],
        address=payload["address"],
        items=payload["items"],
        delivery_location=payload["delivery_location"],
        notes=payload["notes"],
        promo_code_value=payload["promo_code"],
    )
    if error:
        return _service_error_response(error)

    audit_event = log_request_audit_event(
        actor_user_id=user.id if user else None,
        action="storefront.checkout_order_created",
        entity_type="order",
        entity_id=order.id,
        message="Checkout order created from storefront checkout flow.",
        target_repr=order.order_number,
        metadata={
            "guest_checkout": user is None,
            "order_number": order.order_number,
            "tracking_token": order.tracking_token,
            "total_amount": order.total_amount_value,
        },
    )
    if audit_event is not None:
        db.session.add(audit_event)
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)}), 201


@checkout_bp.get("/orders/<string:tracking_token>")
def get_checkout_order(tracking_token: str):
    order = get_order_for_tracking_token(tracking_token=tracking_token)
    if order is None:
        return not_found_response("Order not found.")
    return jsonify({"item": serialize_order(order, include_items=True)})


@checkout_bp.post("/payments")
def create_checkout_payment():
    payload = validate_checkout_payment_payload(get_json_payload())
    if "errors" in payload:
        return validation_error(payload["errors"])

    user = _resolve_optional_user()
    payment, error, status_code = create_payment_for_order(
        user_id=user.id if user else None,
        order_id=payload["order_id"],
        method=payload["method"],
        phone_number=payload["phone_number"],
        callback_base_url=current_app.config["PAYMENT_CALLBACK_BASE_URL"],
        reconciliation_timeout_minutes=current_app.config["MPESA_RECONCILIATION_TIMEOUT_MINUTES"],
        tracking_token=payload["tracking_token"],
    )
    if error:
        if error.code == "validation_error":
            return validation_error(error.details or {"payment": error.message})
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status_code

    audit_event = log_request_audit_event(
        actor_user_id=user.id if user else None,
        action="storefront.checkout_payment_created",
        entity_type="payment",
        entity_id=payment.id,
        message="Checkout payment initiated from storefront checkout flow.",
        target_repr=payment.reference,
        metadata={
            "order_id": payment.order_id,
            "method": payment.method.value,
            "status": payment.status.value,
            "guest_checkout": user is None,
        },
    )
    if audit_event is not None:
        db.session.add(audit_event)
    db.session.commit()
    return jsonify({"item": serialize_payment(payment)}), status_code
