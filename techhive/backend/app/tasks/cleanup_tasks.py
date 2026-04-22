from datetime import datetime, timezone


def build_cleanup_summary(*, cleaned_items: int, task_name: str) -> dict:
    return {
        "task_name": task_name,
        "cleaned_items": cleaned_items,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
