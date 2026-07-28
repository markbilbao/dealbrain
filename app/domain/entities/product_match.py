"""Product matching result value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain.entities.canonical_product import CanonicalProduct


class MatchType(StrEnum):
    """Classification of a product-title / canonical comparison."""

    EXACT_VARIANT = "exact_variant"
    PROBABLE_VARIANT = "probable_variant"
    SAME_PRODUCT_DIFFERENT_VARIANT = "same_product_different_variant"
    DIFFERENT_PRODUCT = "different_product"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class FieldCompareStatus(StrEnum):
    """Per-field comparison outcome used by the matcher."""

    MATCHED = "matched"
    CONFLICT = "conflict"
    MISSING_A = "missing_a"
    MISSING_B = "missing_b"
    BOTH_ABSENT = "both_absent"


@dataclass(frozen=True, slots=True)
class FieldConflict:
    """A field that disagrees between two listings."""

    field: str
    value_a: str
    value_b: str


@dataclass(frozen=True, slots=True)
class ProductMatchResult:
    """Explainable outcome of comparing two parsed canonical products."""

    is_match: bool
    confidence: float
    match_type: MatchType
    matched_fields: tuple[str, ...] = ()
    conflicts: tuple[FieldConflict, ...] = ()
    explanation: tuple[str, ...] = ()
    product_a: CanonicalProduct | None = None
    product_b: CanonicalProduct | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the public match decision (excludes attached products)."""
        return {
            "is_match": self.is_match,
            "confidence": self.confidence,
            "match_type": self.match_type.value,
            "matched_fields": list(self.matched_fields),
            "conflicts": [
                {
                    "field": conflict.field,
                    "value_a": conflict.value_a,
                    "value_b": conflict.value_b,
                }
                for conflict in self.conflicts
            ],
            "explanation": list(self.explanation),
        }
