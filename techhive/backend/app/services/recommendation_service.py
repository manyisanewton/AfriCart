from collections import Counter

from app.models import CartItem, OrderItem, Product, Review, WishlistItem


def _product_priority(product, score: int):
    average_rating = product.average_rating or 0
    return (
        score,
        int(product.is_featured),
        average_rating,
        product.review_count,
        product.id,
    )


def generic_recommendations(limit: int = 6) -> list[Product]:
    products = Product.query.filter_by(is_active=True).all()
    ranked = sorted(
        [product for product in products if product.stock_quantity > 0],
        key=lambda product: _product_priority(product, 0),
        reverse=True,
    )
    return ranked[:limit]


def personalized_recommendations(user_id: int, limit: int = 6) -> list[Product]:
    category_weights: Counter[int] = Counter()
    brand_weights: Counter[int] = Counter()
    interacted_product_ids: set[int] = set()

    signal_groups = [
        (CartItem.query.filter_by(user_id=user_id).all(), 2),
        (WishlistItem.query.filter_by(user_id=user_id).all(), 3),
        (Review.query.filter_by(user_id=user_id).all(), 4),
        (
            OrderItem.query.join(OrderItem.order)
            .filter_by(user_id=user_id)
            .all(),
            5,
        ),
    ]

    for items, weight in signal_groups:
        for item in items:
            product = item.product
            if product is None:
                continue
            interacted_product_ids.add(product.id)
            category_weights[product.category_id] += weight
            brand_weights[product.brand_id] += weight

    if not category_weights and not brand_weights:
        return generic_recommendations(limit)

    products = (
        Product.query.filter(Product.is_active.is_(True))
        .filter(Product.stock_quantity > 0)
        .all()
    )

    scored_products = []
    for product in products:
        if product.id in interacted_product_ids:
            continue

        score = category_weights[product.category_id] + brand_weights[product.brand_id]
        if score <= 0:
            continue

        scored_products.append((product, score))

    if not scored_products:
        return generic_recommendations(limit)

    ranked = sorted(
        scored_products,
        key=lambda item: _product_priority(item[0], item[1]),
        reverse=True,
    )
    return [product for product, _score in ranked[:limit]]
