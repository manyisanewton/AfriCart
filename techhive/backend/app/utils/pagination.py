def normalize_pagination(
    *,
    page: int | None,
    per_page: int | None,
    default_per_page: int = 10,
    max_per_page: int = 50,
) -> tuple[int, int]:
    normalized_page = max(page or 1, 1)
    normalized_per_page = per_page or default_per_page
    normalized_per_page = min(max(normalized_per_page, 1), max_per_page)
    return normalized_page, normalized_per_page


def build_pagination_metadata(*, page: int, per_page: int, total: int) -> dict:
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }
