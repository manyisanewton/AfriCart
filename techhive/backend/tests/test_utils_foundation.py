from app.utils.api import parse_positive_int
from app.utils.helpers import format_money
from app.utils.pagination import build_pagination_metadata, normalize_pagination
from app.utils.validators import parse_allowed_origins, parse_bool


def test_normalize_pagination_applies_bounds():
    page, per_page = normalize_pagination(page=-4, per_page=200)

    assert page == 1
    assert per_page == 50


def test_build_pagination_metadata_calculates_total_pages():
    payload = build_pagination_metadata(page=2, per_page=10, total=23)

    assert payload == {
        "page": 2,
        "per_page": 10,
        "total": 23,
        "total_pages": 3,
    }


def test_parse_bool_handles_common_variants():
    assert parse_bool("true") is True
    assert parse_bool("0") is False
    assert parse_bool("unknown", default=None) is None


def test_parse_allowed_origins_splits_csv_values():
    assert parse_allowed_origins("https://a.com, https://b.com") == {
        "https://a.com",
        "https://b.com",
    }


def test_format_money_returns_consistent_string():
    assert format_money(12) == "12.00"
    assert format_money("9.5") == "9.50"
    assert format_money(None) is None


def test_parse_positive_int_returns_error_for_invalid_values():
    parsed, errors = parse_positive_int("zero", field_name="limit")

    assert parsed is None
    assert errors == {"limit": "limit must be a positive integer."}


def test_parse_positive_int_reads_positive_numbers():
    parsed, errors = parse_positive_int("7", field_name="limit")

    assert parsed == 7
    assert errors is None
