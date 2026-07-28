"""Unit tests for ExactVariantProductMatcher."""

import pytest
from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_match import MatchType
from app.domain.interfaces.product_matcher import ProductMatcher
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser


@pytest.fixture
def parser() -> RuleBasedProductParser:
    return RuleBasedProductParser()


@pytest.fixture
def matcher() -> ExactVariantProductMatcher:
    return ExactVariantProductMatcher()


def _match_titles(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
    title_a: str,
    title_b: str,
):
    return matcher.match_products(parser.parse(title_a), parser.parse(title_b))


def test_matcher_implements_port(matcher: ExactVariantProductMatcher) -> None:
    assert isinstance(matcher, ProductMatcher)
    assert matcher.matcher_name == "exact_variant_product_matcher"


def test_positive_iphone_abbreviation_match(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(
        matcher,
        parser,
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256 BT",
    )
    assert result.is_match is True
    assert result.match_type == MatchType.EXACT_VARIANT
    assert result.confidence >= 0.95
    assert set(result.matched_fields) >= {"brand", "family", "model", "storage", "color"}
    assert result.conflicts == ()
    assert any("17 Pro Max" in line for line in result.explanation)
    assert any("256GB" in line for line in result.explanation)
    assert any("Black Titanium" in line for line in result.explanation)


def test_positive_airpods_abbreviation_match(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(
        matcher,
        parser,
        "AirPods Pro 2 USB-C",
        "Apple APP2 Type C",
    )
    assert result.is_match is True
    assert result.match_type in {MatchType.EXACT_VARIANT, MatchType.PROBABLE_VARIANT}
    assert "family" in result.matched_fields
    assert "model" in result.matched_fields
    assert "connector" in result.matched_fields
    assert result.conflicts == ()


def test_negative_pro_vs_pro_max(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(matcher, parser, "iPhone 17 Pro 256GB", "iPhone 17 Pro Max 256GB")
    assert result.is_match is False
    assert result.match_type == MatchType.DIFFERENT_PRODUCT
    assert any(c.field == "model" for c in result.conflicts)


def test_negative_storage_conflict(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(
        matcher,
        parser,
        "iPhone 17 Pro Max 256GB",
        "iPhone 17 Pro Max 512GB",
    )
    assert result.is_match is False
    assert result.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(c.field == "storage" for c in result.conflicts)
    assert "model" in result.matched_fields


def test_negative_macbook_air_vs_pro(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(
        matcher,
        parser,
        "MacBook Air M5 13-inch",
        "MacBook Pro M5 14-inch",
    )
    assert result.is_match is False
    assert result.match_type == MatchType.DIFFERENT_PRODUCT
    assert any(c.field == "family" for c in result.conflicts)


def test_missing_optional_color_reduces_confidence_not_reject(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    full = _match_titles(
        matcher,
        parser,
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256 BT",
    )
    partial = _match_titles(
        matcher,
        parser,
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256",
    )
    assert partial.is_match is True
    assert partial.match_type in {MatchType.EXACT_VARIANT, MatchType.PROBABLE_VARIANT}
    assert partial.confidence < full.confidence
    assert partial.conflicts == ()
    assert any("confidence reduced" in line.lower() for line in partial.explanation)


def test_insufficient_information(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(matcher, parser, "mystery gadget", "another unknown thing")
    assert result.is_match is False
    assert result.match_type == MatchType.INSUFFICIENT_INFORMATION


def test_match_products_accepts_parsed_objects(matcher: ExactVariantProductMatcher) -> None:
    a = CanonicalProduct(
        brand="Apple",
        family="iPhone",
        model="17 Pro Max",
        storage="256GB",
        color="Black Titanium",
        confidence=0.9,
    )
    b = CanonicalProduct(
        brand="Apple",
        family="iPhone",
        model="17 Pro Max",
        storage="256GB",
        color="Black Titanium",
        confidence=0.85,
    )
    result = matcher.match_products(a, b)
    assert result.is_match is True
    assert result.match_type == MatchType.EXACT_VARIANT


def test_color_conflict_is_variant_difference(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    result = _match_titles(
        matcher,
        parser,
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256 WT",
    )
    assert result.is_match is False
    assert result.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(c.field == "color" for c in result.conflicts)


def test_explanations_are_always_present(
    matcher: ExactVariantProductMatcher,
    parser: RuleBasedProductParser,
) -> None:
    cases = [
        ("Apple IP17PM 256 BT", "Apple iPhone 17 Pro Max 256GB Black Titanium"),
        ("iPhone 17 Pro 256GB", "iPhone 17 Pro Max 256GB"),
        ("unknown", "also unknown"),
    ]
    for title_a, title_b in cases:
        result = _match_titles(matcher, parser, title_a, title_b)
        assert len(result.explanation) >= 1


def test_matcher_is_independently_testable_without_registry(
    matcher: ExactVariantProductMatcher,
) -> None:
    """Matcher depends only on CanonicalProduct inputs — no registry coupling."""
    result = matcher.match_products(
        CanonicalProduct(brand="Apple", family="iPhone", model="15"),
        CanonicalProduct(brand="Apple", family="iPhone", model="15"),
    )
    assert result.is_match is True
