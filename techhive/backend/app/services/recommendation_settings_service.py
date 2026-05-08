from __future__ import annotations

from app.models import PlatformSetting


RECOMMENDATION_SETTING_KEYS = {
    "popularity_blend_weight": {
        "db_key": "recommendation.popularity_blend_weight",
        "type": float,
        "default": 0.35,
        "min": 0.0,
        "max": 2.0,
    },
    "trending_window_days": {
        "db_key": "recommendation.trending_window_days",
        "type": int,
        "default": 14,
        "min": 1,
        "max": 90,
    },
    "trending_reason_threshold": {
        "db_key": "recommendation.trending_reason_threshold",
        "type": float,
        "default": 3.0,
        "min": 0.0,
        "max": 20.0,
    },
    "max_brand_recommendations": {
        "db_key": "recommendation.max_brand_recommendations",
        "type": int,
        "default": 2,
        "min": 1,
        "max": 10,
    },
    "max_vendor_recommendations": {
        "db_key": "recommendation.max_vendor_recommendations",
        "type": int,
        "default": 4,
        "min": 1,
        "max": 20,
    },
    "max_category_recommendations": {
        "db_key": "recommendation.max_category_recommendations",
        "type": int,
        "default": 3,
        "min": 1,
        "max": 20,
    },
}


def _coerce_setting(raw_value: str | None, config: dict):
    if raw_value in (None, ""):
        return config["default"]
    try:
        value = config["type"](raw_value)
    except (TypeError, ValueError):
        return config["default"]
    return max(config["min"], min(config["max"], value))


def get_recommendation_settings() -> dict:
    db_keys = [config["db_key"] for config in RECOMMENDATION_SETTING_KEYS.values()]
    stored = {
        setting.key: setting.value
        for setting in PlatformSetting.query.filter(PlatformSetting.key.in_(db_keys)).all()
    }
    return {
        name: _coerce_setting(stored.get(config["db_key"]), config)
        for name, config in RECOMMENDATION_SETTING_KEYS.items()
    }


def serialize_recommendation_settings() -> list[dict]:
    settings = get_recommendation_settings()
    return [
        {
            "key": name,
            "db_key": config["db_key"],
            "value": settings[name],
            "default": config["default"],
            "min": config["min"],
            "max": config["max"],
        }
        for name, config in RECOMMENDATION_SETTING_KEYS.items()
    ]
