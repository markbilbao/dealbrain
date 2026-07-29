"""Deterministic recommendation ranking for the shopping assistant."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import (
    ShoppingCandidate,
    ShoppingEvidence,
    ShoppingIntent,
    ShoppingRecommendation,
)


class ShoppingRecommendationRanker:
    """Rank candidates with deterministic DealScore / rating / constraint logic.

    Application-layer name ``ShoppingRecommendationService`` in the sprint brief
    maps here to avoid colliding with
    ``app.services.shopping_recommendation_service.ShoppingRecommendationService``.
    """

    def rank(
        self,
        candidates: list[ShoppingCandidate],
        evidence: list[ShoppingEvidence],
        intent: ShoppingIntent,
        *,
        limit: int = 3,
    ) -> list[ShoppingRecommendation]:
        if not candidates:
            return []

        ranked = sorted(
            candidates,
            key=lambda item: (
                item.match_score,
                item.deal_score or 0.0,
                item.rating or 0.0,
                item.review_count,
                -(item.known_price or 0.0),
            ),
            reverse=True,
        )

        recommendations: list[ShoppingRecommendation] = []
        for candidate in ranked[:limit]:
            evidence_ids = tuple(
                item.evidence_id for item in evidence if item.product_id == candidate.product_id
            )
            reason = self._reason(candidate, intent)
            confidence = self._item_confidence(candidate, evidence_ids)
            recommendations.append(
                ShoppingRecommendation(
                    product_id=candidate.product_id,
                    product_name=candidate.product_name,
                    reason=reason,
                    known_price=candidate.known_price,
                    currency=candidate.currency,
                    marketplace=candidate.marketplace,
                    deal_score=candidate.deal_score,
                    confidence=confidence,
                    evidence_ids=evidence_ids,
                    rating=candidate.rating,
                    review_count=candidate.review_count,
                )
            )
        return recommendations

    def _reason(self, candidate: ShoppingCandidate, intent: ShoppingIntent) -> str:
        parts: list[str] = []
        if candidate.deal_score is not None:
            parts.append(f"DealScore {candidate.deal_score:.1f}")
        if candidate.known_price is not None:
            budget = intent.constraints.budget_max
            price_bit = f"known price {candidate.known_price:,.0f} {candidate.currency}"
            if budget is not None:
                price_bit += (
                    f" within budget ₱{budget:,.0f}"
                    if candidate.currency == "PHP"
                    else (f" within budget {budget:,.0f} {candidate.currency}")
                )
            parts.append(price_bit)
        if intent.constraints.use_cases:
            matched = [u for u in intent.constraints.use_cases if u in candidate.use_cases]
            if matched:
                parts.append("matches use case(s): " + ", ".join(matched))
        if candidate.rating is not None:
            parts.append(f"rating {candidate.rating:.2f} ({candidate.review_count:,} reviews)")
        if candidate.marketplace:
            parts.append(f"offer on {candidate.marketplace}")
        if not parts:
            return "Best available match among mock/imported catalog candidates."
        return "Supported by " + "; ".join(parts) + "."

    @staticmethod
    def _item_confidence(candidate: ShoppingCandidate, evidence_ids: tuple[str, ...]) -> float:
        score = 0.35
        score += min(0.25, 0.04 * len(evidence_ids))
        if candidate.deal_score is not None:
            score += 0.12
        if candidate.rating is not None and candidate.review_count >= 100:
            score += 0.12
        elif candidate.rating is not None:
            score += 0.06
        if candidate.known_price is not None and candidate.marketplace:
            score += 0.08
        if candidate.data_status == "live":
            score += 0.05
        elif candidate.data_status == "imported":
            score += 0.02
        return round(min(0.92, score), 2)
