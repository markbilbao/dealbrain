"""Mutable parse context shared across rule applications.

Working buffer only — freeze into :class:`CanonicalProduct` when complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.entities.canonical_product import CanonicalProduct, ParseSignal
from app.intelligence.product_parser.tokenizer import Token

_SETTABLE_ATTRIBUTES = frozenset(
    {"brand", "family", "model", "storage", "color", "connector", "screen_size"}
)


@dataclass
class ParseContext:
    """Working state for a single product-name parse pass."""

    raw_input: str
    tokens: list[Token]
    consumed: set[int] = field(default_factory=set)
    brand: str | None = None
    family: str | None = None
    model: str | None = None
    storage: str | None = None
    color: str | None = None
    connector: str | None = None
    screen_size: str | None = None
    signals: list[ParseSignal] = field(default_factory=list)

    def available_tokens(self) -> list[Token]:
        """Return tokens not yet claimed by a rule."""
        return [t for t in self.tokens if t.index not in self.consumed]

    def consume(self, *indices: int) -> None:
        """Mark token indices as consumed."""
        self.consumed.update(indices)

    def add_signal(
        self,
        *,
        attribute: str,
        value: str,
        rule_id: str,
        weight: float,
        source_span: str | None = None,
    ) -> None:
        """Record an extraction signal for confidence / explainability."""
        self.signals.append(
            ParseSignal(
                attribute=attribute,
                value=value,
                rule_id=rule_id,
                weight=weight,
                source_span=source_span,
            )
        )

    def set_attribute(
        self,
        attribute: str,
        value: str,
        *,
        rule_id: str,
        weight: float,
        source: str,
    ) -> bool:
        """Set a canonical attribute once; returns False if already set."""
        if attribute not in _SETTABLE_ATTRIBUTES:
            raise ValueError(f"Unknown parse attribute: {attribute}")
        if getattr(self, attribute) is not None:
            return False
        setattr(self, attribute, value)
        self.add_signal(
            attribute=attribute,
            value=value,
            rule_id=rule_id,
            weight=weight,
            source_span=source,
        )
        return True

    def set_brand(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute("brand", value, rule_id=rule_id, weight=weight, source=source)

    def set_family(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute("family", value, rule_id=rule_id, weight=weight, source=source)

    def set_model(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute("model", value, rule_id=rule_id, weight=weight, source=source)

    def set_storage(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute("storage", value, rule_id=rule_id, weight=weight, source=source)

    def set_color(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute("color", value, rule_id=rule_id, weight=weight, source=source)

    def set_connector(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute(
            "connector", value, rule_id=rule_id, weight=weight, source=source
        )

    def set_screen_size(self, value: str, *, rule_id: str, weight: float, source: str) -> bool:
        return self.set_attribute(
            "screen_size", value, rule_id=rule_id, weight=weight, source=source
        )

    def to_partial_product(self, confidence: float) -> CanonicalProduct:
        """Freeze context into an immutable canonical product."""
        return CanonicalProduct(
            brand=self.brand,
            family=self.family,
            model=self.model,
            storage=self.storage,
            color=self.color,
            connector=self.connector,
            screen_size=self.screen_size,
            confidence=confidence,
            raw_input=self.raw_input,
            signals=tuple(self.signals),
        )
