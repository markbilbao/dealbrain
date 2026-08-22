"""Capture helper for schema 1.2 decision-time presentation facts.

Copies caller-supplied shopper context, qualification, product identity, fit
evidence, and Recommendation reasoning. Does not invent missing fields or
mutate the original snapshot.
"""

from __future__ import annotations

from dataclasses import replace

from app.domain.entities.decision_presentation import (
    CanonicalAlternativeTradeoff,
    CanonicalBestFor,
    CanonicalProductPresentation,
    CanonicalQualification,
    CanonicalRecommendationReason,
    CanonicalShopperContext,
)
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot


def attach_presentation_contract(
    snapshot: CanonicalDecisionSnapshot,
    *,
    qualification: CanonicalQualification | None = None,
    shopper_context: CanonicalShopperContext | None = None,
    product_presentation: tuple[CanonicalProductPresentation, ...] = (),
    recommendation_reasons: tuple[CanonicalRecommendationReason, ...] = (),
    best_for: tuple[CanonicalBestFor, ...] = (),
    alternative_tradeoffs: tuple[CanonicalAlternativeTradeoff, ...] = (),
    data_classification: str | None = None,
) -> CanonicalDecisionSnapshot:
    """Return a new snapshot that includes captured presentation facts."""

    return replace(
        snapshot,
        qualification=qualification if qualification is not None else snapshot.qualification,
        shopper_context=(
            shopper_context if shopper_context is not None else snapshot.shopper_context
        ),
        product_presentation=product_presentation or snapshot.product_presentation,
        recommendation_reasons=recommendation_reasons or snapshot.recommendation_reasons,
        best_for=best_for or snapshot.best_for,
        alternative_tradeoffs=alternative_tradeoffs or snapshot.alternative_tradeoffs,
        data_classification=data_classification or snapshot.data_classification,
    )
