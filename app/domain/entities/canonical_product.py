"""Canonical product value objects produced by Product Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParseSignal:
    """Evidence that an attribute was extracted from a raw product name.

    Signals support explainability and confidence scoring without coupling
    the domain to a specific rule implementation.
    """

    attribute: str
    value: str
    rule_id: str
    weight: float
    source_span: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalProduct:
    """Structured product representation derived from a messy listing title."""

    brand: str | None = None
    family: str | None = None
    model: str | None = None
    storage: str | None = None
    color: str | None = None
    connector: str | None = None
    screen_size: str | None = None
    confidence: float = 0.0
    raw_input: str | None = None
    signals: tuple[ParseSignal, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, str | float | None]:
        """Serialize the primary canonical fields."""
        return {
            "brand": self.brand,
            "family": self.family,
            "model": self.model,
            "storage": self.storage,
            "color": self.color,
            "connector": self.connector,
            "screen_size": self.screen_size,
            "confidence": self.confidence,
        }
