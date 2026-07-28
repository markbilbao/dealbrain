"""Confidence scoring for parsed canonical products."""

from __future__ import annotations

from app.domain.entities.canonical_product import ParseSignal

# Target attribute weights — sum to 1.0 for a fully specified product.
ATTRIBUTE_WEIGHTS: dict[str, float] = {
    "brand": 0.25,
    "family": 0.25,
    "model": 0.25,
    "storage": 0.15,
    "color": 0.10,
}

# Soft penalty when family/model exist without brand (weaker identity).
MISSING_BRAND_PENALTY = 0.05


def score_confidence(signals: list[ParseSignal] | tuple[ParseSignal, ...]) -> float:
    """Compute a deterministic confidence score in ``[0.0, 1.0]``.

    For each attribute, take the max signal weight (capped at 1.0) and
    scale by the attribute's contribution to a complete parse.
    """
    if not signals:
        return 0.0

    best_by_attr: dict[str, float] = {}
    for signal in signals:
        if signal.attribute not in ATTRIBUTE_WEIGHTS:
            continue
        strength = max(0.0, min(1.0, signal.weight))
        prev = best_by_attr.get(signal.attribute, 0.0)
        if strength > prev:
            best_by_attr[signal.attribute] = strength

    score = 0.0
    for attribute, attr_weight in ATTRIBUTE_WEIGHTS.items():
        score += attr_weight * best_by_attr.get(attribute, 0.0)

    has_identity = "family" in best_by_attr or "model" in best_by_attr
    if has_identity and "brand" not in best_by_attr:
        score = max(0.0, score - MISSING_BRAND_PENALTY)

    return round(min(1.0, score), 2)
