from flask import g, jsonify, request

from app.blueprints.auth.helpers import validation_error
from app.blueprints.reviews import reviews_bp
from app.blueprints.reviews.schemas import validate_review_payload
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import OrderItem, Product, Review


def serialize_review(review: Review) -> dict:
    return {
        "id": review.id,
        "rating": review.rating,
        "title": review.title,
        "comment": review.comment,
        "is_verified_buyer": review.is_verified_buyer,
        "user": {
            "id": review.user.id,
            "full_name": review.user.full_name,
        },
        "created_at": review.created_at.isoformat(),
    }


def serialize_review_summary(product: Product) -> dict:
    counts = {str(star): 0 for star in range(1, 6)}
    for review in product.reviews:
        counts[str(review.rating)] += 1

    return {
        "average_rating": product.average_rating,
        "review_count": product.review_count,
        "distribution": counts,
    }


@reviews_bp.get("/products/<string:slug>/reviews")
def list_product_reviews(slug: str):
    """
    List public reviews for a product.
    ---
    tags:
      - Reviews
    responses:
      200:
        description: Product reviews and summary.
      404:
        description: Product not found.
    """
    product = Product.query.filter_by(slug=slug, is_active=True).first()
    if product is None:
        return jsonify({"error": {"code": "not_found", "message": "Product not found."}}), 404

    reviews = (
        Review.query.filter_by(product_id=product.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .all()
    )
    return jsonify(
        {
            "summary": serialize_review_summary(product),
            "items": [serialize_review(review) for review in reviews],
        }
    )


@reviews_bp.post("/reviews")
@auth_required
def create_review():
    """
    Create a verified-buyer review for a purchased product.
    ---
    tags:
      - Reviews
    responses:
      201:
        description: Review created.
    """
    payload = validate_review_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    product = Product.query.filter_by(id=payload["product_id"], is_active=True).first()
    if product is None:
        return jsonify({"error": {"code": "not_found", "message": "Product not found."}}), 404

    if Review.query.filter_by(user_id=g.current_user.id, product_id=product.id).first():
        return validation_error({"product_id": "You have already reviewed this product."})

    has_purchased = (
        db.session.query(OrderItem.id)
        .join(OrderItem.order)
        .filter(
            OrderItem.product_id == product.id,
            OrderItem.order.has(user_id=g.current_user.id),
        )
        .first()
        is not None
    )
    if not has_purchased:
        return validation_error(
            {"product_id": "You can only review products you have purchased."}
        )

    review = Review(
        user_id=g.current_user.id,
        product_id=product.id,
        rating=payload["rating"],
        title=payload["title"],
        comment=payload["comment"],
        is_verified_buyer=True,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"item": serialize_review(review)}), 201
