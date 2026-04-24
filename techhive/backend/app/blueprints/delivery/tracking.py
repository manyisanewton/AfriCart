from datetime import datetime, timezone

from app.models import DeliveryZone


def resolve_delivery_zone(city: str | None):
    if not city:
        return None
    return DeliveryZone.query.filter(
        DeliveryZone.city.ilike(city.strip()),
        DeliveryZone.is_active.is_(True),
    ).first()


def generate_tracking_token(order_number: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{order_number}-{timestamp}"
