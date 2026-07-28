"""Deterministic exact-variant product matcher.

Compares two :class:`~app.domain.entities.canonical_product.CanonicalProduct`
values produced by the Product Intelligence parser. Does not parse titles and
does not touch the registry or marketplaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_match import (
    FieldCompareStatus,
    FieldConflict,
    MatchType,
    ProductMatchResult,
)
from app.domain.identity import has_matchable_identity, normalize_whitespace
from app.domain.interfaces.product_matcher import ProductMatcher

# Core identity — conflicts mean different products.
IDENTITY_FIELDS: tuple[str, ...] = ("brand", "family", "model")

# Variant dimensions — conflicts mean same product line, different SKU/variant.
VARIANT_FIELDS: tuple[str, ...] = ("storage", "color", "connector", "screen_size")

COMPARISON_FIELDS: tuple[str, ...] = IDENTITY_FIELDS + VARIANT_FIELDS


@dataclass(frozen=True, slots=True)
class _FieldOutcome:
    """Internal per-field comparison record."""

    field: str
    status: FieldCompareStatus
    value_a: str | None
    value_b: str | None


class ExactVariantProductMatcher(ProductMatcher):
    """Compare listings by normalized canonical attributes.

    Missing optional fields reduce confidence; conflicting model/storage/etc.
    prevent an exact match. Every decision emits human-readable explanations.
    """

    @property
    def matcher_name(self) -> str:
        return "exact_variant_product_matcher"

    def match_products(
        self,
        product_a: CanonicalProduct,
        product_b: CanonicalProduct,
    ) -> ProductMatchResult:
        """Compare two already-parsed canonical products."""
        outcomes = [_compare_field(product_a, product_b, name) for name in COMPARISON_FIELDS]

        matched = tuple(o.field for o in outcomes if o.status is FieldCompareStatus.MATCHED)
        conflicts = tuple(
            FieldConflict(field=o.field, value_a=o.value_a or "", value_b=o.value_b or "")
            for o in outcomes
            if o.status is FieldCompareStatus.CONFLICT
        )
        one_sided = [
            o
            for o in outcomes
            if o.status in {FieldCompareStatus.MISSING_A, FieldCompareStatus.MISSING_B}
        ]

        identity_conflicts = [c for c in conflicts if c.field in IDENTITY_FIELDS]
        variant_conflicts = [c for c in conflicts if c.field in VARIANT_FIELDS]
        identity_matched = [f for f in matched if f in IDENTITY_FIELDS]

        has_identity_a = has_matchable_identity(product_a)
        has_identity_b = has_matchable_identity(product_b)

        if not has_identity_a or not has_identity_b:
            explanation = _insufficient_explanation(
                product_a, product_b, has_identity_a, has_identity_b
            )
            return ProductMatchResult(
                is_match=False,
                confidence=0.15 if identity_matched else 0.05,
                match_type=MatchType.INSUFFICIENT_INFORMATION,
                matched_fields=matched,
                conflicts=conflicts,
                explanation=tuple(explanation),
                product_a=product_a,
                product_b=product_b,
            )

        if identity_conflicts:
            explanation = _different_product_explanation(identity_conflicts, identity_matched)
            confidence = round(0.2 + 0.1 * len(identity_matched), 2)
            return ProductMatchResult(
                is_match=False,
                confidence=min(confidence, 0.55),
                match_type=MatchType.DIFFERENT_PRODUCT,
                matched_fields=matched,
                conflicts=conflicts,
                explanation=tuple(explanation),
                product_a=product_a,
                product_b=product_b,
            )

        if variant_conflicts:
            explanation = _variant_conflict_explanation(
                product_a,
                product_b,
                identity_matched,
                variant_conflicts,
            )
            confidence = round(0.55 + 0.08 * len(identity_matched), 2)
            return ProductMatchResult(
                is_match=False,
                confidence=min(confidence, 0.85),
                match_type=MatchType.SAME_PRODUCT_DIFFERENT_VARIANT,
                matched_fields=matched,
                conflicts=conflicts,
                explanation=tuple(explanation),
                product_a=product_a,
                product_b=product_b,
            )

        confidence = _score_positive_match(matched, one_sided, identity_matched)
        explanation = _positive_explanation(product_a, product_b, matched, one_sided)

        if len(identity_matched) < 3 or len(one_sided) >= 2:
            match_type = MatchType.PROBABLE_VARIANT
            confidence = min(confidence, 0.9)
        else:
            match_type = MatchType.EXACT_VARIANT

        return ProductMatchResult(
            is_match=True,
            confidence=confidence,
            match_type=match_type,
            matched_fields=matched,
            conflicts=(),
            explanation=tuple(explanation),
            product_a=product_a,
            product_b=product_b,
        )


def _field_value(product: CanonicalProduct, field_name: str) -> str | None:
    raw = getattr(product, field_name, None)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _compare_field(
    product_a: CanonicalProduct,
    product_b: CanonicalProduct,
    field_name: str,
) -> _FieldOutcome:
    value_a = _field_value(product_a, field_name)
    value_b = _field_value(product_b, field_name)

    if value_a is None and value_b is None:
        return _FieldOutcome(field_name, FieldCompareStatus.BOTH_ABSENT, None, None)
    if value_a is None:
        return _FieldOutcome(field_name, FieldCompareStatus.MISSING_A, None, value_b)
    if value_b is None:
        return _FieldOutcome(field_name, FieldCompareStatus.MISSING_B, value_a, None)
    if normalize_whitespace(value_a) == normalize_whitespace(value_b):
        return _FieldOutcome(field_name, FieldCompareStatus.MATCHED, value_a, value_b)
    return _FieldOutcome(field_name, FieldCompareStatus.CONFLICT, value_a, value_b)


def _score_positive_match(
    matched: tuple[str, ...],
    one_sided: list[_FieldOutcome],
    identity_matched: list[str],
) -> float:
    """Score a conflict-free match.

    Confidence formula (documented for V1 stability):
    - base 0.70 + 0.07 per matched identity field
    - +0.03 per matched variant field
    - −0.03 per one-sided optional field
    """
    score = 0.7 + 0.07 * len(identity_matched)
    variant_matched = [f for f in matched if f in VARIANT_FIELDS]
    score += 0.03 * len(variant_matched)
    score -= 0.03 * len(one_sided)
    return round(min(max(score, 0.5), 0.99), 2)


def _product_label(product: CanonicalProduct) -> str:
    parts = [product.brand, product.family, product.model]
    return " ".join(p for p in parts if p) or "unknown product"


def _insufficient_explanation(
    product_a: CanonicalProduct,
    product_b: CanonicalProduct,
    has_a: bool,
    has_b: bool,
) -> list[str]:
    lines: list[str] = []
    if not has_a and not has_b:
        lines.append("Insufficient information on both listings to identify a product variant.")
    elif not has_a:
        lines.append(
            f"Listing A lacks enough identity fields to compare against {_product_label(product_b)}."
        )
    else:
        lines.append(
            f"Listing B lacks enough identity fields to compare against {_product_label(product_a)}."
        )
    return lines


def _different_product_explanation(
    identity_conflicts: list[FieldConflict],
    identity_matched: list[str],
) -> list[str]:
    lines: list[str] = ["Listings refer to different products."]
    for conflict in identity_conflicts:
        lines.append(
            f"{conflict.field.capitalize()} conflicts: "
            f"{conflict.value_a!r} vs {conflict.value_b!r}."
        )
    if identity_matched:
        lines.append(f"Agreed identity fields: {', '.join(identity_matched)}.")
    return lines


def _variant_conflict_explanation(
    product_a: CanonicalProduct,
    product_b: CanonicalProduct,
    identity_matched: list[str],
    variant_conflicts: list[FieldConflict],
) -> list[str]:
    label = _product_label(product_a) if identity_matched else "the same product line"
    lines = [f"Both listings appear to be {label}, but variants differ."]
    for conflict in variant_conflicts:
        lines.append(
            f"{conflict.field.replace('_', ' ').capitalize()} conflicts: "
            f"{conflict.value_a!r} vs {conflict.value_b!r}."
        )
    return lines


def _positive_explanation(
    product_a: CanonicalProduct,
    product_b: CanonicalProduct,
    matched: tuple[str, ...],
    one_sided: list[_FieldOutcome],
) -> list[str]:
    lines: list[str] = []
    label = _product_label(product_a)
    if {"brand", "family", "model"} <= set(matched) or (
        "family" in matched and "model" in matched
    ):
        lines.append(f"Both listings resolve to {label}.")
    elif matched:
        lines.append(f"Listings agree on: {', '.join(matched)}.")

    if "storage" in matched:
        lines.append(f"Storage matches at {product_a.storage}.")
    if "color" in matched:
        lines.append(_color_explanation(product_a, product_b))
    if "connector" in matched:
        lines.append(f"Connector matches at {product_a.connector}.")
    if "screen_size" in matched:
        lines.append(f"Screen size matches at {product_a.screen_size}.")

    for outcome in one_sided:
        present = outcome.value_a or outcome.value_b
        side = "A" if outcome.status is FieldCompareStatus.MISSING_B else "B"
        lines.append(
            f"{outcome.field.replace('_', ' ').capitalize()} "
            f"({present}) is present only on listing {side}; confidence reduced."
        )

    if not lines:
        lines.append("No conflicting attributes detected, but evidence is limited.")
    return lines


def _color_explanation(product_a: CanonicalProduct, product_b: CanonicalProduct) -> str:
    """Prefer a normalization note when abbreviations appear in parse signals."""
    color = product_a.color or product_b.color or ""
    for product in (product_a, product_b):
        for signal in product.signals:
            if signal.attribute != "color":
                continue
            if signal.source_span and signal.source_span.lower() != color.lower():
                return f"{signal.source_span} was normalized to {color}."
    return f"Color matches at {color}."
