from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_section(
    *,
    links: dict | None = None,
    items: list | None = None,
    total_count: int | None = None,
    limit: int | None = None,
    empty_message: str | None = None,
    **payload,
) -> dict:
    section = {**payload}
    if links is not None:
        section["links"] = links
    if items is not None:
        section["items"] = items
        resolved_total = total_count if total_count is not None else len(items)
        section["meta"] = {
            "total_count": resolved_total,
            "returned_count": len(items),
            "limit": limit,
            "has_more": resolved_total > len(items),
            "empty_message": empty_message,
        }
    return section
