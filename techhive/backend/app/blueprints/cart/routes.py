from decimal import Decimal

from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.cart import cart_bp
from app.blueprints.cart.schemas import (
    validate_cart_item_payload,
    validate_product_id_payload,
    validate_quantity_payload,
)
from app.blueprints.products.schemas import serialize_product
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import CartItem, Product, WishlistItem


def _cart_item_payload(item: CartItem) -> dict:
    return {
        "id": item.id,
        "quantity": item.quantity,
        "line_total": item.line_total,
        "product": serialize_product(item.product),
    }


def _cart_response(user_id: int):
    items = (
        CartItem.query.filter_by(user_id=user_id)
        .order_by(CartItem.created_at.asc(), CartItem.id.asc())
        .all()
    )
    subtotal = sum(Decimal(item.product.price) * item.quantity for item in items)
    return jsonify(
        {
            "items": [_cart_item_payload(item) for item in items],
            "summary": {
                "items_count": sum(item.quantity for item in items),
                "subtotal": f"{subtotal:.2f}",
                "discount_amount": "0.00",
                "total": f"{subtotal:.2f}",
            },
        }
    )


def _wishlist_response(user_id: int):
    items = (
        WishlistItem.query.filter_by(user_id=user_id)
        .order_by(WishlistItem.created_at.asc(), WishlistItem.id.asc())
        .all()
    )
    return jsonify(
        {
            "items": [
                {
                    "id": item.id,
                    "product": serialize_product(item.product),
                }
                for item in items
            ]
        }
    )


def _load_active_product(product_id: int):
    return Product.query.filter_by(id=product_id, is_active=True).first()


@cart_bp.get("/cart")
@auth_required
def get_cart():
    """
    Get the authenticated user's cart.
    ---
    tags:
      - Cart
    responses:
      200:
        description: Current cart contents.
    """
    return _cart_response(g.current_user.id)


@cart_bp.post("/cart/items")
@auth_required
def add_cart_item():
    """
    Add a product to the authenticated user's cart.
    ---
    tags:
      - Cart
    responses:
      201:
        description: Product added to cart.
    """
    payload = validate_cart_item_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = _load_active_product(payload["product_id"])
    if product is None:
        return (
            jsonify({"error": {"code": "not_found", "message": "Product not found."}}),
            404,
        )

    if payload["quantity"] > product.stock_quantity:
        return validation_error(
            {"quantity": "Requested quantity exceeds available stock."}
        )

    item = CartItem.query.filter_by(
        user_id=g.current_user.id,
        product_id=product.id,
    ).first()
    if item is None:
        item = CartItem(
            user_id=g.current_user.id,
            product_id=product.id,
            quantity=payload["quantity"],
        )
        db.session.add(item)
    else:
        new_quantity = item.quantity + payload["quantity"]
        if new_quantity > product.stock_quantity:
            return validation_error(
                {"quantity": "Requested quantity exceeds available stock."}
            )
        item.quantity = new_quantity

    db.session.commit()
    return jsonify({"item": _cart_item_payload(item)}), 201


@cart_bp.patch("/cart/items/<int:item_id>")
@auth_required
def update_cart_item(item_id: int):
    """
    Update cart item quantity.
    ---
    tags:
      - Cart
    responses:
      200:
        description: Cart item updated.
    """
    payload = validate_quantity_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    item = CartItem.query.filter_by(id=item_id, user_id=g.current_user.id).first()
    if item is None:
        return (
            jsonify({"error": {"code": "not_found", "message": "Cart item not found."}}),
            404,
        )

    if payload["quantity"] > item.product.stock_quantity:
        return validation_error(
            {"quantity": "Requested quantity exceeds available stock."}
        )

    item.quantity = payload["quantity"]
    db.session.commit()
    return jsonify({"item": _cart_item_payload(item)})


@cart_bp.delete("/cart/items/<int:item_id>")
@auth_required
def delete_cart_item(item_id: int):
    """
    Remove a product from the cart.
    ---
    tags:
      - Cart
    responses:
      200:
        description: Cart item removed.
    """
    item = CartItem.query.filter_by(id=item_id, user_id=g.current_user.id).first()
    if item is None:
        return (
            jsonify({"error": {"code": "not_found", "message": "Cart item not found."}}),
            404,
        )

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Cart item removed."})


@cart_bp.get("/wishlist")
@auth_required
def get_wishlist():
    """
    Get the authenticated user's wishlist.
    ---
    tags:
      - Wishlist
    responses:
      200:
        description: Current wishlist contents.
    """
    return _wishlist_response(g.current_user.id)


@cart_bp.post("/wishlist/items")
@auth_required
def add_wishlist_item():
    """
    Add a product to the authenticated user's wishlist.
    ---
    tags:
      - Wishlist
    responses:
      201:
        description: Product added to wishlist.
    """
    payload = validate_cart_item_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = _load_active_product(payload["product_id"])
    if product is None:
        return (
            jsonify({"error": {"code": "not_found", "message": "Product not found."}}),
            404,
        )

    existing = WishlistItem.query.filter_by(
        user_id=g.current_user.id,
        product_id=product.id,
    ).first()
    if existing is not None:
        return jsonify({"item": {"id": existing.id, "product": serialize_product(product)}}), 200

    item = WishlistItem(user_id=g.current_user.id, product_id=product.id)
    db.session.add(item)
    db.session.commit()
    return jsonify({"item": {"id": item.id, "product": serialize_product(product)}}), 201


@cart_bp.delete("/wishlist/items/<int:item_id>")
@auth_required
def delete_wishlist_item(item_id: int):
    """
    Remove a product from the wishlist.
    ---
    tags:
      - Wishlist
    responses:
      200:
        description: Wishlist item removed.
    """
    item = WishlistItem.query.filter_by(id=item_id, user_id=g.current_user.id).first()
    if item is None:
        return (
            jsonify(
                {"error": {"code": "not_found", "message": "Wishlist item not found."}}
            ),
            404,
        )

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Wishlist item removed."})
