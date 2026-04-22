from datetime import datetime, timezone


def build_daily_sales_report(*, total_orders: int, gross_sales: str) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_orders": total_orders,
        "gross_sales": gross_sales,
    }
