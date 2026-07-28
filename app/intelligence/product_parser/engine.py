"""Deterministic rule-based product name parser."""

from __future__ import annotations

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.intelligence.product_parser.confidence import score_confidence
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules import ParseRule, default_rules
from app.intelligence.product_parser.tokenizer import tokenize


class RuleBasedProductParser(ProductIntelligenceEngine):
    """Extensible product intelligence engine driven by ordered parse rules.

    Pipeline:
        1. Tokenize the raw listing title
        2. Apply rules in priority order (brand → family/model → storage → color)
        3. Score confidence from extraction signals
    """

    def __init__(self, rules: list[ParseRule] | None = None) -> None:
        self._rules = sorted(rules if rules is not None else default_rules(), key=lambda r: r.priority)

    @property
    def engine_name(self) -> str:
        return "rule_based_product_parser"

    @property
    def rules(self) -> tuple[ParseRule, ...]:
        """Registered rules in execution order."""
        return tuple(self._rules)

    def parse(self, raw_name: str) -> CanonicalProduct:
        """Parse a messy product name into a structured canonical product."""
        if raw_name is None:
            raise TypeError("raw_name must be a string")

        text = raw_name.strip()
        tokens = tokenize(text)
        context = ParseContext(raw_input=text, tokens=tokens)

        if not tokens:
            return context.to_partial_product(confidence=0.0)

        for rule in self._rules:
            rule.apply(context)

        confidence = score_confidence(context.signals)
        return context.to_partial_product(confidence=confidence)
