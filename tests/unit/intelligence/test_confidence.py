"""Unit tests for confidence scoring."""

from app.domain.entities.canonical_product import ParseSignal
from app.intelligence.product_parser.confidence import score_confidence


def test_empty_signals_zero_confidence() -> None:
    assert score_confidence([]) == 0.0


def test_full_high_weight_signals_near_one() -> None:
    signals = [
        ParseSignal("brand", "Apple", "brand.alias", 1.0, "Apple"),
        ParseSignal("family", "iPhone", "family_model.apple", 1.0, "IP17PM"),
        ParseSignal("model", "17 Pro Max", "family_model.apple", 1.0, "IP17PM"),
        ParseSignal("storage", "256GB", "storage.capacity", 1.0, "256"),
        ParseSignal("color", "Black Titanium", "color.alias", 1.0, "BT"),
    ]
    assert score_confidence(signals) == 1.0


def test_partial_parse_scales_by_attribute_weights() -> None:
    signals = [
        ParseSignal("brand", "Apple", "brand.alias", 1.0, "Apple"),
        ParseSignal("family", "iPhone", "family_model.apple", 1.0, "IP"),
    ]
    # brand 0.25 + family 0.25 = 0.5
    assert score_confidence(signals) == 0.5


def test_missing_brand_penalty_when_identity_present() -> None:
    signals = [
        ParseSignal("family", "iPhone", "family_model.apple", 1.0, "IP17PM"),
        ParseSignal("model", "17 Pro Max", "family_model.apple", 1.0, "IP17PM"),
    ]
    # family 0.25 + model 0.25 - 0.05 penalty = 0.45
    assert score_confidence(signals) == 0.45
