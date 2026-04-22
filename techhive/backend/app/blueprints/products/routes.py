from datetime import datetime, timezone

from flask import g, jsonify, request

from app.blueprints.products import products_bp
from app.blueprints.products.search import build_product_query, search_suggestions
from app.blueprints.products.schemas import (
    serialize_brand,
    serialize_banner,
    serialize_category,
    serialize_flash_sale,
    serialize_product,
)
from app.middleware.auth_required import auth_required
from app.models import Banner, Brand, Category, FlashSale, Product
from app.services.recommendation_service import personalized_recommendations


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _pagination_metadata(page: int, per_page: int, total: int) -> dict:
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


@products_bp.get("/categories")
def list_categories():
    """
    List active product categories.
    ---
    tags:
      - Products
    responses:
      200:
        description: Active categories.
    """
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    return jsonify({"items": [serialize_category(category) for category in categories]})


@products_bp.get("/brands")
def list_brands():
    """
    List active product brands.
    ---
    tags:
      - Products
    responses:
      200:
        description: Active brands.
    """
    brands = Brand.query.filter_by(is_active=True).order_by(Brand.name.asc()).all()
    return jsonify({"items": [serialize_brand(brand) for brand in brands]})


@products_bp.get("/products")
def list_products():
    """
    List public active products with basic filters.
    ---
    tags:
      - Products
    responses:
      200:
        description: Paginated product list.
    """
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = min(max(request.args.get("per_page", default=10, type=int), 1), 50)
    category_slug = request.args.get("category")
    brand_slug = request.args.get("brand")
    featured = request.args.get("featured")
    q = request.args.get("q", default="", type=str).strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    in_stock = request.args.get("in_stock")
    sort = request.args.get("sort")

    query = build_product_query(
        category_slug=category_slug,
        brand_slug=brand_slug,
        featured=featured,
        q=q,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort=sort,
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "items": [serialize_product(product) for product in pagination.items],
            "pagination": _pagination_metadata(page, per_page, pagination.total),
        }
    )


@products_bp.get("/banners")
def list_banners():
    """
    List active public storefront banners.
    ---
    tags:
      - Products
    responses:
      200:
        description: Active banners.
    """
    now = _utc_now()
    banners = (
        Banner.query.filter_by(is_active=True)
        .filter((Banner.starts_at.is_(None)) | (Banner.starts_at <= now))
        .filter((Banner.ends_at.is_(None)) | (Banner.ends_at >= now))
        .order_by(Banner.sort_order.asc(), Banner.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_banner(banner) for banner in banners]})


@products_bp.get("/flash-sales")
def list_flash_sales():
    """
    List active public flash sales.
    ---
    tags:
      - Products
    responses:
      200:
        description: Active flash sales.
    """
    now = _utc_now()
    flash_sales = (
        FlashSale.query.join(Product, FlashSale.product)
        .filter(FlashSale.is_active.is_(True), Product.is_active.is_(True))
        .filter(FlashSale.starts_at <= now, FlashSale.ends_at >= now)
        .order_by(FlashSale.ends_at.asc(), FlashSale.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_flash_sale(flash_sale) for flash_sale in flash_sales]})


@products_bp.get("/products/<string:slug>")
def get_product(slug: str):
    """
    Get a public product by slug.
    ---
    tags:
      - Products
    responses:
      200:
        description: Product details.
      404:
        description: Product not found.
    """
    product = Product.query.filter_by(slug=slug, is_active=True).first()
    if product is None:
        return (
            jsonify(
                {
                    "error": {
                        "code": "not_found",
                        "message": "Product not found.",
                    }
                }
            ),
            404,
        )

    return jsonify({"item": serialize_product(product, include_related=True)})


@products_bp.get("/products/autocomplete")
def autocomplete_products():
    """
    Suggest product names for a search query.
    ---
    tags:
      - Products
    responses:
      200:
        description: Product suggestions.
    """
    q = request.args.get("q", default="", type=str)
    items = search_suggestions(q)
    return jsonify(
        {
            "items": [
                {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                }
                for product in items
            ]
        }
    )


@products_bp.get("/products/recommendations")
@auth_required
def list_recommendations():
    """
    List personalized product recommendations for the authenticated user.
    ---
    tags:
      - Products
    security:
      - Bearer: []
    responses:
      200:
        description: Recommended products.
    """
    limit = min(max(request.args.get("limit", default=6, type=int), 1), 20)
    items = personalized_recommendations(g.current_user.id, limit=limit)
    return jsonify({"items": [serialize_product(product) for product in items]})
