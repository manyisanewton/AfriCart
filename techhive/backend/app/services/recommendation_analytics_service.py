from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.models import RecommendationEvent


EVENT_IMPRESSION = "impression"
EVENT_CLICK = "click"


def log_recommendation_impressions(*, user_id: int, mode: str, items: list[dict]) -> list[RecommendationEvent]:
    return [
        RecommendationEvent(
            user_id=user_id,
            product_id=item["product"].id,
            event_type=EVENT_IMPRESSION,
            mode=mode,
            reason_code=item["reason_code"],
        )
        for item in items
    ]


def log_recommendation_click(*, user_id: int, product_id: int, mode: str, reason_code: str) -> RecommendationEvent:
    return RecommendationEvent(
        user_id=user_id,
        product_id=product_id,
        event_type=EVENT_CLICK,
        mode=mode,
        reason_code=reason_code,
    )


def summarize_recommendation_metrics(*, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = (
        RecommendationEvent.query.filter(RecommendationEvent.created_at >= cutoff)
        .order_by(RecommendationEvent.created_at.desc(), RecommendationEvent.id.desc())
        .all()
    )

    impressions = [event for event in events if event.event_type == EVENT_IMPRESSION]
    clicks = [event for event in events if event.event_type == EVENT_CLICK]
    clicks_by_mode = Counter(event.mode for event in clicks)
    impressions_by_mode = Counter(event.mode for event in impressions)
    impressions_by_reason = Counter(event.reason_code for event in impressions)
    clicks_by_reason = Counter(event.reason_code for event in clicks)

    return {
        "days": days,
        "summary": {
            "impressions": len(impressions),
            "clicks": len(clicks),
            "ctr": round((len(clicks) / len(impressions)), 4) if impressions else 0.0,
        },
        "by_mode": [
            {
                "mode": mode,
                "impressions": impressions_by_mode[mode],
                "clicks": clicks_by_mode[mode],
                "ctr": round((clicks_by_mode[mode] / impressions_by_mode[mode]), 4)
                if impressions_by_mode[mode]
                else 0.0,
            }
            for mode in sorted(set(impressions_by_mode) | set(clicks_by_mode))
        ],
        "by_reason_code": [
            {
                "reason_code": reason_code,
                "impressions": impressions_by_reason[reason_code],
                "clicks": clicks_by_reason[reason_code],
                "ctr": round((clicks_by_reason[reason_code] / impressions_by_reason[reason_code]), 4)
                if impressions_by_reason[reason_code]
                else 0.0,
            }
            for reason_code in sorted(set(impressions_by_reason) | set(clicks_by_reason))
        ],
    }
