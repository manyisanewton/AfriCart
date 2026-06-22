from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from app.blueprints.delivery.tracking import resolve_delivery_zone
from app.models import PlatformSetting, Product


DELIVERY_SETTING_KEYS = {
    "origin_latitude": {
        "db_key": "delivery.origin_latitude",
        "type": float,
        "default": -1.286389,
    },
    "origin_longitude": {
        "db_key": "delivery.origin_longitude",
        "type": float,
        "default": 36.817223,
    },
    "origin_label": {
        "db_key": "delivery.origin_label",
        "type": str,
        "default": "TechHive dispatch centre",
    },
    "base_fee": {
        "db_key": "delivery.base_fee",
        "type": Decimal,
        "default": Decimal("150.00"),
    },
    "per_km_fee": {
        "db_key": "delivery.per_km_fee",
        "type": Decimal,
        "default": Decimal("35.00"),
    },
    "per_kg_fee": {
        "db_key": "delivery.per_kg_fee",
        "type": Decimal,
        "default": Decimal("25.00"),
    },
    "minimum_fee": {
        "db_key": "delivery.minimum_fee",
        "type": Decimal,
        "default": Decimal("150.00"),
    },
    "free_distance_km": {
        "db_key": "delivery.free_distance_km",
        "type": float,
        "default": 0.0,
    },
    "max_service_distance_km": {
        "db_key": "delivery.max_service_distance_km",
        "type": float,
        "default": 80.0,
    },
}


@dataclass
class DeliveryQuote:
    shipping_amount: Decimal
    delivery_zone_name: str | None
    distance_km: Decimal | None
    weight_grams: int
    weight_charge: Decimal
    distance_charge: Decimal
    base_fee: Decimal
    method: str
    origin_label: str | None


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _coerce_setting(raw_value: str | None, config: dict):
    if raw_value in (None, ""):
        return config["default"]
    try:
        if config["type"] is Decimal:
            return Decimal(str(raw_value))
        return config["type"](raw_value)
    except (TypeError, ValueError, ArithmeticError):
        return config["default"]


def get_delivery_pricing_settings() -> dict:
    db_keys = [config["db_key"] for config in DELIVERY_SETTING_KEYS.values()]
    stored = {
        setting.key: setting.value
        for setting in PlatformSetting.query.filter(PlatformSetting.key.in_(db_keys)).all()
    }
    return {
        name: _coerce_setting(stored.get(config["db_key"]), config)
        for name, config in DELIVERY_SETTING_KEYS.items()
    }


def calculate_cart_weight_grams(items: list[tuple[Product, int]]) -> int:
    total = 0
    for product, quantity in items:
        item_weight = int(product.weight_grams or 0)
        total += max(item_weight, 0) * quantity
    return total


def _calculate_distance_km(*, origin_lat: float, origin_lng: float, destination_lat: float, destination_lng: float) -> Decimal:
    radius_km = 6371.0
    lat_delta = radians(destination_lat - origin_lat)
    lng_delta = radians(destination_lng - origin_lng)
    origin_lat_rad = radians(origin_lat)
    destination_lat_rad = radians(destination_lat)
    haversine = sin(lat_delta / 2) ** 2 + cos(origin_lat_rad) * cos(destination_lat_rad) * sin(lng_delta / 2) ** 2
    distance = 2 * radius_km * asin(sqrt(haversine))
    return Decimal(str(distance)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quote_delivery(*, address: dict, items: list[tuple[Product, int]], delivery_location: dict | None = None) -> tuple[DeliveryQuote | None, dict[str, str] | None]:
    settings = get_delivery_pricing_settings()
    total_weight_grams = calculate_cart_weight_grams(items)

    if delivery_location and delivery_location.get("latitude") is not None and delivery_location.get("longitude") is not None:
        distance_km = _calculate_distance_km(
            origin_lat=float(settings["origin_latitude"]),
            origin_lng=float(settings["origin_longitude"]),
            destination_lat=float(delivery_location["latitude"]),
            destination_lng=float(delivery_location["longitude"]),
        )
        if Decimal(str(distance_km)) > Decimal(str(settings["max_service_distance_km"])):
            return None, {
                "delivery_location": f"Delivery distance exceeds the current service radius of {settings['max_service_distance_km']} km."
            }

        billable_distance = max(float(distance_km) - float(settings["free_distance_km"]), 0.0)
        distance_charge = _quantize_money(Decimal(str(billable_distance)) * Decimal(settings["per_km_fee"]))
        weight_charge = _quantize_money((Decimal(total_weight_grams) / Decimal("1000")) * Decimal(settings["per_kg_fee"]))
        shipping_amount = _quantize_money(Decimal(settings["base_fee"]) + distance_charge + weight_charge)
        shipping_amount = max(shipping_amount, Decimal(settings["minimum_fee"]))

        return DeliveryQuote(
            shipping_amount=shipping_amount,
            delivery_zone_name=None,
            distance_km=distance_km,
            weight_grams=total_weight_grams,
            weight_charge=weight_charge,
            distance_charge=distance_charge,
            base_fee=_quantize_money(Decimal(settings["base_fee"])),
            method="distance_weight",
            origin_label=str(settings["origin_label"]),
        ), None

    zone = resolve_delivery_zone(address["city"])
    shipping_amount = _quantize_money(Decimal(zone.fee) if zone is not None else Decimal("0.00"))
    return DeliveryQuote(
        shipping_amount=shipping_amount,
        delivery_zone_name=zone.name if zone is not None else None,
        distance_km=None,
        weight_grams=total_weight_grams,
        weight_charge=Decimal("0.00"),
        distance_charge=Decimal("0.00"),
        base_fee=shipping_amount,
        method="delivery_zone",
        origin_label=str(settings["origin_label"]),
    ), None
