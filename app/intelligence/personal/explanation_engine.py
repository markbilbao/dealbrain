"""Explanation engine — evidence-grounded personalization narratives."""

from __future__ import annotations

from typing import Any

from app.domain.entities.personal_agent import (
    BuyingAdvice,
    CustomerProfile,
    PersonalDealScore,
    PersonalRecommendation,
    PreferenceScoreResult,
)


class ExplanationEngine:
    """Build short explanations that cite preference and DealScore evidence only."""

    def explain_recommendation(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        *,
        preference: PreferenceScoreResult,
        personal_score: PersonalDealScore,
        advice: BuyingAdvice | None = None,
    ) -> str:
        name = str(product.get("product_name") or product.get("product_id") or "Product")
        top_dims = sorted(
            preference.dimensions,
            key=lambda d: d.weighted_score,
            reverse=True,
        )[:3]
        dim_text = ", ".join(
            f"{d.dimension}={round(d.score, 2)}" for d in top_dims if d.weighted_score > 0
        )
        parts = [
            f"For {profile.display_name}, {name} scores PersonalDealScore "
            f"{personal_score.personal_deal_score}",
        ]
        if personal_score.global_deal_score is not None:
            parts.append(f"(global DealScore {personal_score.global_deal_score})")
        parts.append(f"with preference total {round(preference.total_score, 2)}")
        if dim_text:
            parts.append(f"led by {dim_text}")
        if advice is not None:
            parts.append(f"— advisor: {advice.label}")
        text = " ".join(parts) + "."
        return text

    def explain_personal_deal_score(self, score: PersonalDealScore) -> str:
        return (
            f"PersonalDealScore {score.personal_deal_score} combines global DealScore "
            f"{score.global_deal_score}, preference_fit {round(score.preference_fit, 2)}, "
            f"budget_fit {round(score.budget_fit, 2)}, brand_affinity "
            f"{round(score.brand_affinity, 2)}, ownership_compatibility "
            f"{round(score.ownership_compatibility, 2)}, and community_trust "
            f"{round(score.community_trust, 2)}."
        )

    def reason_line(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        personal_score: PersonalDealScore,
        advice: BuyingAdvice | None,
    ) -> str:
        label = advice.label if advice else "Personalized match"
        budget_bit = ""
        if profile.budget is not None and product.get("known_price") is not None:
            budget_bit = (
                f" Price {product.get('known_price')} {profile.currency} vs budget "
                f"{profile.budget}."
            )
        return (
            f"{label} for {profile.display_name} "
            f"(PersonalDealScore {personal_score.personal_deal_score}).{budget_bit}"
        )

    def attach_explanation(self, recommendation: PersonalRecommendation) -> PersonalRecommendation:
        """Return recommendation unchanged when explanation already present."""
        if recommendation.explanation.strip():
            return recommendation
        return recommendation
