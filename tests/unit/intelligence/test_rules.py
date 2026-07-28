"""Unit tests for individual parse rules."""

from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.brand import BrandRule
from app.intelligence.product_parser.rules.color import ColorRule
from app.intelligence.product_parser.rules.family_model import FamilyModelRule
from app.intelligence.product_parser.rules.storage import StorageRule
from app.intelligence.product_parser.tokenizer import tokenize


def _context(raw: str) -> ParseContext:
    return ParseContext(raw_input=raw, tokens=tokenize(raw))


def test_brand_rule_matches_apple() -> None:
    ctx = _context("Apple IP17PM")
    BrandRule().apply(ctx)
    assert ctx.brand == "Apple"
    assert 0 in ctx.consumed


def test_brand_rule_is_idempotent() -> None:
    ctx = _context("Apple Samsung")
    BrandRule().apply(ctx)
    BrandRule().apply(ctx)
    assert ctx.brand == "Apple"
    assert len([s for s in ctx.signals if s.attribute == "brand"]) == 1


def test_family_model_rule_compound() -> None:
    ctx = _context("IP17PM")
    FamilyModelRule().apply(ctx)
    assert ctx.family == "iPhone"
    assert ctx.model == "17 Pro Max"


def test_family_model_rule_spaced() -> None:
    ctx = _context("iPhone 17 Pro Max")
    FamilyModelRule().apply(ctx)
    assert ctx.family == "iPhone"
    assert ctx.model == "17 Pro Max"


def test_family_model_rule_requires_apple_context_for_bare_tier_code() -> None:
    ctx = _context("17PM 256")
    FamilyModelRule().apply(ctx)
    assert ctx.family is None
    assert ctx.model is None

    ctx.brand = "Apple"
    FamilyModelRule().apply(ctx)
    assert ctx.family == "iPhone"
    assert ctx.model == "17 Pro Max"


def test_storage_rule_bare_and_explicit() -> None:
    ctx = _context("256")
    StorageRule().apply(ctx)
    assert ctx.storage == "256GB"

    ctx2 = _context("1TB")
    StorageRule().apply(ctx2)
    assert ctx2.storage == "1TB"


def test_color_rule_code_and_name() -> None:
    ctx = _context("BT")
    ColorRule().apply(ctx)
    assert ctx.color == "Black Titanium"

    ctx2 = _context("Desert Titanium")
    ColorRule().apply(ctx2)
    assert ctx2.color == "Desert Titanium"
