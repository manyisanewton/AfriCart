from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models import Product, ProductView


def record_product_view(*, user_id: int, product: Product) -> ProductView:
    product_view = ProductView.query.filter_by(user_id=user_id, product_id=product.id).first()
    if product_view is None:
        product_view = ProductView(user_id=user_id, product_id=product.id)
        db.session.add(product_view)
        db.session.flush()
        return product_view

    product_view.view_count += 1
    product_view.last_viewed_at = datetime.now(timezone.utc)
    db.session.flush()
    return product_view


def list_recently_viewed_products(*, user_id: int, limit: int) -> list[ProductView]:
    return (
        ProductView.query.filter_by(user_id=user_id)
        .order_by(ProductView.last_viewed_at.desc(), ProductView.id.desc())
        .limit(limit)
        .all()
    )
