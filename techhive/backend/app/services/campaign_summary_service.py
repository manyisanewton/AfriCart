from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import Offer, OrderItem, Product, ProductRange, PromoCode, Review, SupportTicket, User, UserRole


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _money(value) -> float:
    return float(Decimal(value or 0))


def _product_revenue(product: Product) -> Decimal:
    total = Decimal("0")
    items = OrderItem.query.filter_by(product_id=product.id).all()
    for item in items:
        total += Decimal(item.line_total)
    return total


@dataclass
class CampaignWindow:
    days: int
    start: datetime
    end: datetime


def _build_window(days: int) -> CampaignWindow:
    safe_days = max(1, int(days))
    end = _utc_now()
    start = end - timedelta(days=safe_days)
    return CampaignWindow(days=safe_days, start=start, end=end)


def build_campaign_summary(days: int = 30) -> dict:
    window = _build_window(days)

    total_customers = User.query.filter(User.role == UserRole.CUSTOMER).count()
    active_customers = (
        User.query.filter(
            User.role == UserRole.CUSTOMER,
            User.created_at >= window.start,
        ).count()
    )
    quote_leads = SupportTicket.query.filter(SupportTicket.created_at >= window.start).count()
    draft_products = Product.query.filter_by(is_active=False).count()

    ranges = ProductRange.query.order_by(ProductRange.created_at.desc(), ProductRange.id.desc()).all()
    offers = Offer.query.order_by(Offer.priority.desc(), Offer.created_at.desc()).all()
    vouchers = PromoCode.query.order_by(PromoCode.created_at.desc(), PromoCode.id.desc()).all()

    campaigns: list[dict] = []

    for offer in offers:
        campaigns.append(
            {
                "id": f"offer-{offer.id}",
                "name": offer.name,
                "description": offer.description or f"{offer.offer_type.title()} offer",
                "channel": "Offer",
                "audience": len(vouchers) if offer.offer_type == "voucher" else total_customers,
                "priority": "High" if offer.priority >= 10 else "Medium" if offer.priority >= 5 else "Low",
                "status": "ready" if str(offer.status).lower() == "open" else "blocked",
            }
        )

    for voucher in vouchers:
        state = "ready"
        voucher_ends_at = _coerce_aware(voucher.ends_at)
        if voucher_ends_at and voucher_ends_at < window.end:
            state = "blocked"
        campaigns.append(
            {
                "id": f"voucher-{voucher.id}",
                "name": voucher.name or voucher.code,
                "description": f"{voucher.usage} voucher ({voucher.code})",
                "channel": "Voucher",
                "audience": total_customers,
                "priority": "Medium",
                "status": state,
            }
        )

    for product_range in ranges:
        campaigns.append(
            {
                "id": f"range-{product_range.id}",
                "name": product_range.name,
                "description": product_range.description or "Curated merchandising range",
                "channel": "Range",
                "audience": len(product_range.products) if not product_range.includes_all_products else Product.query.count(),
                "priority": "Low" if product_range.is_public else "Medium",
                "status": "ready",
            }
        )

    approved_reviews = Review.query.filter(Review.status == Review.STATUS_APPROVED).all()
    review_counts = Counter(review.product_id for review in approved_reviews)

    products = Product.query.order_by(Product.created_at.desc(), Product.id.desc()).all()
    product_opportunities = []
    for product in products[:10]:
        revenue = _product_revenue(product)
        order_items = OrderItem.query.filter_by(product_id=product.id).all()
        signal = "Low stock"
        if product.stock_quantity > product.low_stock_threshold:
            signal = "Ready to promote"
        if review_counts.get(product.id, 0) >= 3:
            signal = "Trusted by reviews"

        product_opportunities.append(
            {
                "id": product.id,
                "name": product.name,
                "category": product.category.name if product.category else "Uncategorized",
                "units_sold": sum(item.quantity for item in order_items),
                "revenue": _money(revenue),
                "stock": product.stock_quantity,
                "signal": signal,
            }
        )

    return {
        "range": {
            "days": window.days,
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
        },
        "kpis": {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "quote_leads": quote_leads,
            "draft_products": draft_products,
        },
        "campaigns": campaigns,
        "product_opportunities": product_opportunities,
    }
