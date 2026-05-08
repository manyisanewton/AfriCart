from collections import Counter
from datetime import datetime, timedelta, timezone

from app.models import CartItem, OrderItem, Product, ProductView, Review, WishlistItem
from app.services.recommendation_settings_service import get_recommendation_settings

REASON_LABELS = {
    "trending_now": "Trending now",
    "similar_brand_preference": "Because you like similar brands",
    "similar_category_preference": "Because you like similar categories",
    "price_match": "Within your preferred price range",
    "popular_now": "Popular with shoppers right now",
    "similar_to_product": "Similar to the product you viewed",
    "buy_again": "Buy again",
}


def _product_priority(product, score: float):
    average_rating = product.average_rating or 0
    return (
        score,
        int(product.is_featured),
        average_rating,
        product.review_count,
        product.id,
    )


def _normalize_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _recency_multiplier(timestamp) -> float:
    normalized = _normalize_timestamp(timestamp)
    if normalized is None:
        return 0.4

    age_days = (datetime.now(timezone.utc) - normalized).days
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.7
    return 0.35


def _signal_strength(item) -> float:
    if isinstance(item, ProductView):
        return min(max(item.view_count, 1), 4) * 0.6
    if isinstance(item, CartItem):
        return 1.0 + min(max(item.quantity, 1) - 1, 4) * 0.25
    if isinstance(item, WishlistItem):
        return 1.25
    if isinstance(item, Review):
        return 0.8 + (item.rating / 5.0)
    if isinstance(item, OrderItem):
        return 1.2 + min(max(item.quantity, 1) - 1, 4) * 0.3
    return 1.0


def _price_similarity_bonus(*, candidate_price: float, preferred_price: float | None) -> float:
    if not preferred_price or preferred_price <= 0:
        return 0.0
    distance_ratio = min(abs(candidate_price - preferred_price) / preferred_price, 1.0)
    return (1.0 - distance_ratio) * 2.0


def _market_momentum_scores(products: list[Product], settings: dict) -> dict[int, float]:
    if not products:
        return {}

    product_ids = [product.id for product in products]
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings["trending_window_days"])

    view_scores: Counter[int] = Counter()
    for item in ProductView.query.filter(ProductView.product_id.in_(product_ids)).all():
        score = max(item.view_count, 1) * _recency_multiplier(item.last_viewed_at)
        if _normalize_timestamp(item.last_viewed_at) and _normalize_timestamp(item.last_viewed_at) >= cutoff:
            score *= 1.5
        view_scores[item.product_id] += score

    wishlist_scores: Counter[int] = Counter()
    for item in WishlistItem.query.filter(WishlistItem.product_id.in_(product_ids)).all():
        score = _recency_multiplier(item.created_at)
        if _normalize_timestamp(item.created_at) and _normalize_timestamp(item.created_at) >= cutoff:
            score *= 1.5
        wishlist_scores[item.product_id] += score

    order_scores: Counter[int] = Counter()
    for item in OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all():
        score = max(item.quantity, 1) * _recency_multiplier(item.order.created_at)
        if _normalize_timestamp(item.order.created_at) and _normalize_timestamp(item.order.created_at) >= cutoff:
            score *= 1.6
        order_scores[item.product_id] += score

    review_scores: Counter[int] = Counter()
    for item in Review.query.filter(Review.product_id.in_(product_ids)).all():
        score = (item.rating / 5.0) * _recency_multiplier(item.updated_at or item.created_at)
        if _normalize_timestamp(item.updated_at or item.created_at) and _normalize_timestamp(item.updated_at or item.created_at) >= cutoff:
            score *= 1.25
        review_scores[item.product_id] += score

    momentum_scores: dict[int, float] = {}
    for product in products:
        score = 0.0
        score += view_scores[product.id] * 0.35
        score += wishlist_scores[product.id] * 0.85
        score += order_scores[product.id] * 1.0
        score += review_scores[product.id] * 0.75
        score += (product.average_rating or 0) * 0.2
        score += product.review_count * 0.1
        if product.is_featured:
            score += 0.5
        momentum_scores[product.id] = score

    return momentum_scores


def _build_reason(
    *,
    category_score: float,
    brand_score: float,
    momentum_score: float,
    price_bonus: float,
    settings: dict,
) -> dict:
    if momentum_score >= settings["trending_reason_threshold"] and momentum_score >= max(category_score, brand_score):
        code = "trending_now"
    elif category_score > 0 and brand_score > 0:
        code = "similar_brand_preference"
    elif category_score >= brand_score and category_score > 0:
        code = "similar_category_preference"
    elif brand_score > 0:
        code = "similar_brand_preference"
    elif price_bonus >= 1.0:
        code = "price_match"
    else:
        code = "popular_now"

    return {
        "reason_code": code,
        "reason_label": REASON_LABELS[code],
    }


def _append_diverse_products(
    selected: list[Product],
    candidates: list[Product],
    limit: int,
    settings: dict,
) -> list[Product]:
    brand_counts: Counter[int] = Counter(product.brand_id for product in selected)
    vendor_counts: Counter[int] = Counter(product.vendor_id for product in selected)
    category_counts: Counter[int] = Counter(product.category_id for product in selected)
    selected_ids = {product.id for product in selected}

    for product in candidates:
        if product.id in selected_ids:
            continue
        if (
            brand_counts[product.brand_id] >= settings["max_brand_recommendations"]
            or vendor_counts[product.vendor_id] >= settings["max_vendor_recommendations"]
            or category_counts[product.category_id] >= settings["max_category_recommendations"]
        ):
            continue

        selected.append(product)
        selected_ids.add(product.id)
        brand_counts[product.brand_id] += 1
        vendor_counts[product.vendor_id] += 1
        category_counts[product.category_id] += 1
        if len(selected) >= limit:
            break

    return selected


def _apply_diversity(ranked_products: list[Product], limit: int, settings: dict) -> list[Product]:
    return _append_diverse_products([], ranked_products, limit, settings)


def generic_recommendations(limit: int = 6) -> list[Product]:
    settings = get_recommendation_settings()
    products = Product.query.filter_by(is_active=True).all()
    momentum_scores = _market_momentum_scores(products, settings)
    ranked = sorted(
        [product for product in products if product.stock_quantity > 0],
        key=lambda product: _product_priority(product, momentum_scores.get(product.id, 0.0)),
        reverse=True,
    )
    return _apply_diversity(ranked, limit, settings)


def generic_recommendation_items(limit: int = 6) -> list[dict]:
    settings = get_recommendation_settings()
    products = Product.query.filter_by(is_active=True).all()
    momentum_scores = _market_momentum_scores(products, settings)
    ranked_products = generic_recommendations(limit)
    return [
        {
            "product": product,
            **_build_reason(
                category_score=0.0,
                brand_score=0.0,
                momentum_score=momentum_scores.get(product.id, 0.0),
                price_bonus=0.0,
                settings=settings,
            ),
        }
        for product in ranked_products
    ]


def trending_recommendation_items(limit: int = 6) -> list[dict]:
    return generic_recommendation_items(limit)


def similar_product_recommendation_items(product: Product, limit: int = 6) -> list[dict]:
    settings = get_recommendation_settings()
    products = (
        Product.query.filter(Product.is_active.is_(True))
        .filter(Product.stock_quantity > 0)
        .all()
    )
    momentum_scores = _market_momentum_scores(products, settings)

    scored_products = []
    for candidate in products:
        if candidate.id == product.id:
            continue

        category_score = 2.5 if candidate.category_id == product.category_id else 0.0
        brand_score = 2.0 if candidate.brand_id == product.brand_id else 0.0
        price_bonus = _price_similarity_bonus(
            candidate_price=float(candidate.price),
            preferred_price=float(product.price),
        )
        score = category_score + brand_score + price_bonus
        if category_score > 0 and brand_score > 0:
            score += 1.0
        score += momentum_scores.get(candidate.id, 0.0) * settings["popularity_blend_weight"]
        if score <= 0:
            continue

        scored_products.append((candidate, score))

    ranked = sorted(
        scored_products,
        key=lambda item: _product_priority(item[0], item[1]),
        reverse=True,
    )
    selected_products = _apply_diversity([candidate for candidate, _score in ranked], limit, settings)
    return [
        {
            "product": candidate,
            "reason_code": "similar_to_product",
            "reason_label": REASON_LABELS["similar_to_product"],
        }
        for candidate in selected_products
    ]


def buy_again_recommendation_items(user_id: int, limit: int = 6) -> list[dict]:
    settings = get_recommendation_settings()
    previous_order_items = (
        OrderItem.query.join(OrderItem.order)
        .filter_by(user_id=user_id)
        .all()
    )
    if not previous_order_items:
        return []

    product_scores: Counter[int] = Counter()
    product_lookup: dict[int, Product] = {}
    for item in previous_order_items:
        if item.product is None or not item.product.is_active or item.product.stock_quantity <= 0:
            continue
        product_lookup[item.product_id] = item.product
        score = max(item.quantity, 1) * _recency_multiplier(item.order.created_at) * 2.0
        product_scores[item.product_id] += score

    ranked = sorted(
        [product_lookup[product_id] for product_id in product_scores],
        key=lambda product: _product_priority(product, product_scores[product.id]),
        reverse=True,
    )
    selected_products = _apply_diversity(ranked, limit, settings)
    return [
        {
            "product": product,
            "reason_code": "buy_again",
            "reason_label": REASON_LABELS["buy_again"],
        }
        for product in selected_products
    ]


def personalized_recommendations(user_id: int, limit: int = 6) -> list[Product]:
    return [item["product"] for item in personalized_recommendation_items(user_id, limit=limit)]


def personalized_recommendation_items(user_id: int, limit: int = 6) -> list[dict]:
    settings = get_recommendation_settings()
    category_weights: Counter[int] = Counter()
    brand_weights: Counter[int] = Counter()
    interacted_product_ids: set[int] = set()
    weighted_price_total = 0.0
    weighted_price_weight = 0.0

    signal_groups = [
        (
            ProductView.query.filter_by(user_id=user_id).all(),
            1.0,
            lambda item: item.last_viewed_at,
        ),
        (
            CartItem.query.filter_by(user_id=user_id).all(),
            2.0,
            lambda item: item.updated_at or item.created_at,
        ),
        (
            WishlistItem.query.filter_by(user_id=user_id).all(),
            3.0,
            lambda item: item.created_at,
        ),
        (
            Review.query.filter_by(user_id=user_id).all(),
            4.0,
            lambda item: item.updated_at or item.created_at,
        ),
        (
            OrderItem.query.join(OrderItem.order)
            .filter_by(user_id=user_id)
            .all(),
            5.0,
            lambda item: item.order.created_at,
        ),
    ]

    for items, weight, timestamp_getter in signal_groups:
        for item in items:
            product = item.product
            if product is None:
                continue
            interacted_product_ids.add(product.id)
            adjusted_weight = weight * _recency_multiplier(timestamp_getter(item)) * _signal_strength(item)
            category_weights[product.category_id] += adjusted_weight
            brand_weights[product.brand_id] += adjusted_weight
            weighted_price_total += float(product.price) * adjusted_weight
            weighted_price_weight += adjusted_weight

    if not category_weights and not brand_weights:
        return generic_recommendation_items(limit)

    preferred_price = (
        weighted_price_total / weighted_price_weight if weighted_price_weight > 0 else None
    )

    products = (
        Product.query.filter(Product.is_active.is_(True))
        .filter(Product.stock_quantity > 0)
        .all()
    )
    momentum_scores = _market_momentum_scores(products, settings)

    scored_products = []
    for product in products:
        if product.id in interacted_product_ids:
            continue

        category_score = category_weights[product.category_id]
        brand_score = brand_weights[product.brand_id]
        score = category_score + brand_score
        if category_score > 0 and brand_score > 0:
            score += 1.0
        price_bonus = _price_similarity_bonus(
            candidate_price=float(product.price),
            preferred_price=preferred_price,
        )
        score += price_bonus
        score += momentum_scores.get(product.id, 0.0) * settings["popularity_blend_weight"]
        if score <= 0:
            continue

        scored_products.append(
            (
                product,
                score,
                _build_reason(
                    category_score=category_score,
                    brand_score=brand_score,
                    momentum_score=momentum_scores.get(product.id, 0.0),
                    price_bonus=price_bonus,
                    settings=settings,
                ),
            )
        )

    if not scored_products:
        return generic_recommendation_items(limit)

    ranked = sorted(
        scored_products,
        key=lambda item: _product_priority(item[0], item[1]),
        reverse=True,
    )
    selected_products = _apply_diversity([product for product, _score, _reason in ranked], limit, settings)
    ranked_reason_map = {
        product.id: reason for product, _score, reason in ranked
    }
    selected = [
        {"product": product, **ranked_reason_map[product.id]}
        for product in selected_products
    ]
    if len(selected) >= limit:
        return selected

    fallback_candidates = sorted(
        [
            product
            for product in products
            if product.id not in interacted_product_ids and product.stock_quantity > 0
        ],
        key=lambda product: _product_priority(product, momentum_scores.get(product.id, 0.0)),
        reverse=True,
    )
    fallback_products = _append_diverse_products(
        [item["product"] for item in selected],
        fallback_candidates,
        limit,
        settings,
    )
    selected_ids = {item["product"].id for item in selected}
    for product in fallback_products:
        if product.id in selected_ids:
            continue
        selected.append(
            {
                "product": product,
                **_build_reason(
                    category_score=0.0,
                    brand_score=0.0,
                    momentum_score=momentum_scores.get(product.id, 0.0),
                    price_bonus=0.0,
                    settings=settings,
                ),
            }
        )
        selected_ids.add(product.id)
    return selected
