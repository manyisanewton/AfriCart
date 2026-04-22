def parse_bool(value, *, default: bool | None = None) -> bool | None:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    truthy_values = {"1", "true", "yes", "on"}
    falsy_values = {"0", "false", "no", "off"}

    if normalized in truthy_values:
        return True
    if normalized in falsy_values:
        return False
    return default


def parse_allowed_origins(value: str | None) -> set[str]:
    if not value or value == "*":
        return set()
    return {origin.strip() for origin in value.split(",") if origin.strip()}
