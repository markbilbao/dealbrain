"""Unit tests for the Product Intelligence Engine end-to-end."""

import pytest
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.rules.brand import BrandRule


@pytest.fixture
def parser() -> RuleBasedProductParser:
    return RuleBasedProductParser()


def test_engine_implements_port(parser: RuleBasedProductParser) -> None:
    assert isinstance(parser, ProductIntelligenceEngine)
    assert parser.engine_name == "rule_based_product_parser"


def test_sprint1_golden_example(parser: RuleBasedProductParser) -> None:
    """Apple IP17PM 256 BT → structured canonical product."""
    result = parser.parse("Apple IP17PM 256 BT")

    assert result.brand == "Apple"
    assert result.family == "iPhone"
    assert result.model == "17 Pro Max"
    assert result.storage == "256GB"
    assert result.color == "Black Titanium"
    assert result.confidence >= 0.95
    assert result.to_dict() == {
        "brand": "Apple",
        "family": "iPhone",
        "model": "17 Pro Max",
        "storage": "256GB",
        "color": "Black Titanium",
        "connector": None,
        "screen_size": None,
        "confidence": result.confidence,
    }


def test_spaced_natural_language_title(parser: RuleBasedProductParser) -> None:
    result = parser.parse("Apple iPhone 17 Pro Max 256GB Black Titanium")

    assert result.brand == "Apple"
    assert result.family == "iPhone"
    assert result.model == "17 Pro Max"
    assert result.storage == "256GB"
    assert result.color == "Black Titanium"
    assert result.confidence >= 0.95


@pytest.mark.parametrize(
    ("raw", "brand", "family", "model", "storage", "color"),
    [
        ("Apple IP16P 128 WT", "Apple", "iPhone", "16 Pro", "128GB", "White Titanium"),
        ("Samsung Galaxy placeholder", "Samsung", None, None, None, None),
        ("IP15PM 512 DT", None, "iPhone", "15 Pro Max", "512GB", "Desert Titanium"),
        ("Apple iPhone 15 128GB Blue", "Apple", "iPhone", "15", "128GB", "Blue"),
        ("Google Pixel junk", "Google", None, None, None, None),
    ],
)
def test_varied_listings(
    parser: RuleBasedProductParser,
    raw: str,
    brand: str | None,
    family: str | None,
    model: str | None,
    storage: str | None,
    color: str | None,
) -> None:
    result = parser.parse(raw)
    assert result.brand == brand
    assert result.family == family
    assert result.model == model
    assert result.storage == storage
    assert result.color == color


def test_empty_input_zero_confidence(parser: RuleBasedProductParser) -> None:
    result = parser.parse("")
    assert result.brand is None
    assert result.confidence == 0.0


def test_signals_support_explainability(parser: RuleBasedProductParser) -> None:
    result = parser.parse("Apple IP17PM 256 BT")
    attributes = {signal.attribute for signal in result.signals}
    assert attributes == {"brand", "family", "model", "storage", "color"}
    assert all(signal.rule_id for signal in result.signals)
    assert all(signal.source_span for signal in result.signals)


def test_engine_is_extensible_with_custom_rules() -> None:
    class FixedBrandRule(ParseRule):
        @property
        def rule_id(self) -> str:
            return "brand.fixed"

        @property
        def priority(self) -> int:
            return 1

        def apply(self, context) -> None:  # noqa: ANN001
            context.set_brand("CustomCo", rule_id=self.rule_id, weight=1.0, source="x")

    parser = RuleBasedProductParser(rules=[FixedBrandRule(), BrandRule()])
    result = parser.parse("Apple IP17PM")
    # FixedBrandRule runs first (priority 1) and wins.
    assert result.brand == "CustomCo"
