"""Country selector contract for Early Access."""

from app.core.countries import (
    COUNTRY_CODES,
    country_name,
    is_valid_country_code,
    normalize_country_code,
)


def test_gb_not_uk() -> None:
    assert is_valid_country_code("GB")
    assert not is_valid_country_code("UK")
    assert country_name("GB") == "United Kingdom"


def test_core_markets_present() -> None:
    for code in ("PH", "US", "SG", "GB", "CA"):
        assert code in COUNTRY_CODES


def test_normalize_uppercases() -> None:
    assert normalize_country_code(" ph ") == "PH"
