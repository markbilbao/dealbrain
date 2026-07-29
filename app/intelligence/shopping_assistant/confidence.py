"""Deterministic confidence calculation for shopping assistant answers."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import (
    AssistantConfidence,
    ConfidenceBand,
    ProductComparison,
    ShoppingCandidate,
    ShoppingEvidence,
    ShoppingRecommendation,
)


def confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


class ConfidenceCalculator:
    """Compute confidence from evidence coverage and data quality factors."""

    def calculate(
        self,
        *,
        candidates: list[ShoppingCandidate],
        evidence: list[ShoppingEvidence],
        top: ShoppingRecommendation | None,
        comparison: ProductComparison | None = None,
        provider_agreement: float | None = None,
    ) -> AssistantConfidence:
        factors: list[str] = []
        score = 0.28

        if evidence:
            bonus = min(0.28, 0.03 * len(evidence))
            score += bonus
            factors.append(f"{len(evidence)} evidence items")
        else:
            factors.append("no supporting evidence")

        marketplaces = {item.marketplace for item in candidates if item.marketplace}
        if len(marketplaces) >= 2:
            score += 0.08
            factors.append("multi-marketplace coverage in catalog")
        elif len(marketplaces) == 1:
            score += 0.03
            factors.append("single-marketplace coverage only")
        else:
            factors.append("marketplace coverage missing")

        review_counts = [item.review_count for item in candidates if item.review_count]
        if review_counts and max(review_counts) >= 1000:
            score += 0.1
            factors.append("high review volume available")
        elif review_counts and max(review_counts) >= 100:
            score += 0.06
            factors.append("moderate review volume")
        else:
            factors.append("limited review volume")

        ratings = [item.rating for item in candidates if item.rating is not None]
        if len(ratings) >= 2 and max(ratings) - min(ratings) <= 0.4:
            score += 0.05
            factors.append("rating consistency across candidates")
        elif ratings:
            factors.append("ratings available but mixed")

        missing_attrs = 0
        for item in candidates[:3]:
            if item.known_price is None:
                missing_attrs += 1
            if item.deal_score is None:
                missing_attrs += 1
            if item.rating is None:
                missing_attrs += 1
        if missing_attrs:
            score -= min(0.15, 0.03 * missing_attrs)
            factors.append(f"{missing_attrs} missing numeric attributes")

        if any(item.data_status == "mock" for item in candidates):
            score -= 0.05
            factors.append("mock/demo data in use")

        if top is not None:
            score = max(score, min(0.9, (score + top.confidence) / 2))
            factors.append("top recommendation confidence blended")

        if comparison is not None and comparison.unresolved_uncertainty:
            score -= min(0.1, 0.03 * len(comparison.unresolved_uncertainty))
            factors.append("comparison uncertainties present")

        if provider_agreement is not None:
            score = (score * 0.7) + (provider_agreement * 0.3)
            factors.append(f"provider agreement {provider_agreement:.2f}")

        # Avoid false precision.
        rounded = round(min(0.93, max(0.15, score)), 2)
        return AssistantConfidence(
            score=rounded,
            band=confidence_band(rounded),
            factors=tuple(factors),
        )
