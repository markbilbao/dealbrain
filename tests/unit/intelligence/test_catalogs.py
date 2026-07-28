"""Unit tests for Apple catalog matching and storage normalization."""

from app.intelligence.product_parser.catalogs.apple import match_apple_compound, resolve_tier
from app.intelligence.product_parser.catalogs.storage import normalize_storage


def test_match_ip17pm() -> None:
    matched = match_apple_compound("IP17PM")
    assert matched is not None
    assert matched.family == "iPhone"
    assert matched.model == "17 Pro Max"
    assert matched.generation == "17"
    assert matched.tier == "Pro Max"


def test_match_iph16p() -> None:
    matched = match_apple_compound("IPH16P")
    assert matched is not None
    assert matched.family == "iPhone"
    assert matched.model == "16 Pro"


def test_match_iphone15() -> None:
    matched = match_apple_compound("iPhone15")
    assert matched is not None
    assert matched.family == "iPhone"
    assert matched.model == "15"
    assert matched.tier is None


def test_bare_generation_without_tier_rejected() -> None:
    assert match_apple_compound("17") is None


def test_tiered_generation_without_family_accepted() -> None:
    matched = match_apple_compound("17PM")
    assert matched is not None
    assert matched.family == "iPhone"
    assert matched.model == "17 Pro Max"


def test_resolve_tier() -> None:
    assert resolve_tier("pm") == "Pro Max"
    assert resolve_tier("pro") == "Pro"
    assert resolve_tier("plus") == "Plus"
    assert resolve_tier("unknown") is None


def test_normalize_storage_variants() -> None:
    assert normalize_storage("256") == "256GB"
    assert normalize_storage("256GB") == "256GB"
    assert normalize_storage("256g") == "256GB"
    assert normalize_storage("1TB") == "1TB"
    assert normalize_storage("1t") == "1TB"
    assert normalize_storage("1024") == "1024GB"
    assert normalize_storage("13") is None
