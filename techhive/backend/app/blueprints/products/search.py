from app.models import Brand, Category, Product


def build_product_query(
    *,
    category_slug: str | None = None,
    brand_slug: str | None = None,
    featured: str | None = None,
    q: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: str | None = None,
    sort: str | None = None,
):
    query = Product.query.join(Category).join(Brand).filter(Product.is_active.is_(True))

    if category_slug:
        query = query.filter(Category.slug == category_slug)
    if brand_slug:
        query = query.filter(Brand.slug == brand_slug)
    if featured is not None:
        query = query.filter(Product.is_featured.is_(featured.lower() == "true"))
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            Product.name.ilike(term)
            | Product.short_description.ilike(term)
            | Product.description.ilike(term)
            | Product.sku.ilike(term)
            | Brand.name.ilike(term)
        )
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is not None:
        wants_in_stock = in_stock.lower() == "true"
        if wants_in_stock:
            query = query.filter(Product.stock_quantity > 0)
        else:
            query = query.filter(Product.stock_quantity <= 0)

    sort_key = (sort or "newest").lower()
    if sort_key == "price_asc":
        query = query.order_by(Product.price.asc(), Product.id.desc())
    elif sort_key == "price_desc":
        query = query.order_by(Product.price.desc(), Product.id.desc())
    elif sort_key == "name_asc":
        query = query.order_by(Product.name.asc(), Product.id.desc())
    else:
        query = query.order_by(Product.created_at.desc(), Product.id.desc())

    return query


def search_suggestions(q: str, limit: int = 5):
    term = q.strip()
    if not term:
        return []

    return (
        Product.query.filter(Product.is_active.is_(True), Product.name.ilike(f"%{term}%"))
        .order_by(Product.name.asc(), Product.id.desc())
        .limit(limit)
        .all()
    )
