from decimal import Decimal

from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.promotions import promotions_bp
from app.blueprints.promotions.helpers import validate_promo_code_for_amount
from app.middleware.auth_required import auth_required
from app.models import CartItem, PromoCode
from app.extensions import db
from app.services.audit_service import log_request_audit_event


@promotions_bp.post("/cart/apply-promo")
@auth_required
def apply_promo_to_cart():
    """
    Preview a promo code against the authenticated user's cart.
    ---
    tags:
      - Promotions
    responses:
      200:
        description: Promo preview summary.
    """
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("promo_code") or "").strip().upper()
    if not code:
        return validation_error({"promo_code": "promo_code is required."})

    cart_items = CartItem.query.filter_by(user_id=g.current_user.id).all()
    if not cart_items:
        return validation_error({"cart": "Cart is empty."})

    subtotal = sum(Decimal(item.product.price) * item.quantity for item in cart_items)
    promo_code = PromoCode.query.filter_by(code=code).first()
    discount, error = validate_promo_code_for_amount(promo_code, subtotal)
    if error:
        return validation_error({"promo_code": error})

    total = subtotal - discount
    entity_id = promo_code.id if promo_code is not None else 0
    db.session.add(
        log_request_audit_event(
            actor_user_id=g.current_user.id,
            action="customer.promo_previewed",
            entity_type="promo_code",
            entity_id=entity_id,
            message="Customer previewed a promo code on cart.",
            target_repr=code,
            metadata={"subtotal": f"{subtotal:.2f}", "discount_amount": f"{discount:.2f}"},
        )
    )
    db.session.commit()
    return jsonify(
        {
            "item": {
                "promo_code": code,
                "subtotal": f"{subtotal:.2f}",
                "discount_amount": f"{discount:.2f}",
                "total_after_discount": f"{total:.2f}",
            }
        }
    )
