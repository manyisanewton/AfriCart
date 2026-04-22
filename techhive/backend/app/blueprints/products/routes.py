from flask import jsonify, request

from app.blueprints.products import products_bp
from app.blueprints.products.schemas import (
    serialize_brand,
    serialize_category,
    serialize_product,
)
from app.models import Brand, Category, Product


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

    query = (
        Product.query.join(Category).join(Brand).filter(Product.is_active.is_(True))
    )

    if category_slug:
        query = query.filter(Category.slug == category_slug)
    if brand_slug:
        query = query.filter(Brand.slug == brand_slug)
    if featured is not None:
        query = query.filter(Product.is_featured.is_(featured.lower() == "true"))
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    query = query.order_by(Product.created_at.desc(), Product.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "items": [serialize_product(product) for product in pagination.items],
            "pagination": _pagination_metadata(page, per_page, pagination.total),
        }
    )


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
