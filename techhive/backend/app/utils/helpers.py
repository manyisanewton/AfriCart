from decimal import Decimal


def format_money(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.2f}"
