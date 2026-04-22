from decimal import Decimal

from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.orders import orders_bp
from app.blueprints.orders.helpers import generate_order_number, serialize_order
from app.blueprints.orders.schemas import validate_create_order_payload
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import Address, CartItem, Order, OrderItem, OrderStatus


def _order_not_found():
    return jsonify({"error": {"code": "not_found", "message": "Order not found."}}), 404


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
    payload = validate_create_order_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    address = Address.query.filter_by(
        id=payload["address_id"],
        user_id=g.current_user.id,
    ).first()
    if address is None:
        return validation_error({"address_id": "Selected address was not found."})

    cart_items = (
        CartItem.query.filter_by(user_id=g.current_user.id)
        .order_by(CartItem.created_at.asc(), CartItem.id.asc())
        .all()
    )
    if not cart_items:
        return validation_error({"cart": "Cart is empty."})

    for cart_item in cart_items:
        if cart_item.quantity > cart_item.product.stock_quantity:
            return validation_error(
                {
                    "cart": f"Insufficient stock for product '{cart_item.product.name}'."
                }
            )

    subtotal = sum(Decimal(item.product.price) * item.quantity for item in cart_items)
    shipping_amount = Decimal("0.00")
    order = Order(
        user_id=g.current_user.id,
        order_number=generate_order_number(),
        status=OrderStatus.PENDING,
        currency="KES",
        subtotal=subtotal,
        shipping_amount=shipping_amount,
        total_amount=subtotal + shipping_amount,
        shipping_name=address.recipient_name,
        shipping_phone=address.phone_number,
        shipping_country=address.country,
        shipping_city=address.city,
        shipping_state_or_county=address.state_or_county,
        shipping_postal_code=address.postal_code,
        shipping_address_line_1=address.address_line_1,
        shipping_address_line_2=address.address_line_2,
        notes=payload["notes"],
    )
    db.session.add(order)
    db.session.flush()

    for cart_item in cart_items:
        product = cart_item.product
        line_total = Decimal(product.price) * cart_item.quantity
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            product_slug=product.slug,
            sku=product.sku,
            quantity=cart_item.quantity,
            unit_price=product.price,
            line_total=line_total,
        )
        product.stock_quantity -= cart_item.quantity
        db.session.add(order_item)
        db.session.delete(cart_item)

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
    order = Order.query.filter_by(id=order_id, user_id=g.current_user.id).first()
    if order is None:
        return _order_not_found()
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
    order = Order.query.filter_by(id=order_id, user_id=g.current_user.id).first()
    if order is None:
        return _order_not_found()

    if order.status != OrderStatus.PENDING:
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_state",
                        "message": "Only pending orders can be cancelled.",
                    }
                }
            ),
            400,
        )

    for item in order.items:
        item.product.stock_quantity += item.quantity

    order.status = OrderStatus.CANCELLED
    db.session.commit()
    return jsonify({"item": serialize_order(order, include_items=True)})
