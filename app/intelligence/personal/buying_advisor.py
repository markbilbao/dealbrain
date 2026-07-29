"""Buying advisor — structured, evidence-backed purchase advice."""

from __future__ import annotations

from typing import Any

from app.domain.entities.personal_agent import (
    BuyingAdvice,
    BuyingVerdict,
    CustomerProfile,
    PersonalDealScore,
    PreferenceScoreResult,
)
from app.intelligence.personal.preference_engine import PreferenceEngine
from app.intelligence.personal.scoring_engine import PersonalScoringEngine

VERDICT_LABELS: dict[BuyingVerdict, str] = {
    "excellent_choice": "Excellent choice",
    "good_value": "Good value",
    "worth_waiting": "Worth waiting",
    "price_likely_to_drop": "Price likely to drop",
    "not_recommended": "Not recommended",
    "alternative_available": "Alternative available",
    "upgrade_not_worthwhile": "Upgrade not worthwhile",
    "too_expensive": "Too expensive",
    "poor_community_trust": "Poor community trust",
}


class BuyingAdvisor:
    """Generate structured buying advice from profile + product evidence."""

    def __init__(
        self,
        *,
        preference_engine: PreferenceEngine | None = None,
        scoring_engine: PersonalScoringEngine | None = None,
    ) -> None:
        self._preferences = preference_engine or PreferenceEngine()
        self._scoring = scoring_engine or PersonalScoringEngine(self._preferences)

    def advise(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        *,
        preference: PreferenceScoreResult | None = None,
        personal_score: PersonalDealScore | None = None,
        alternative: dict[str, Any] | None = None,
        community_trust: float | None = None,
    ) -> BuyingAdvice:
        pref = preference or self._preferences.score(
            profile, product, community_sentiment=community_trust
        )
        score = personal_score or self._scoring.score(
            profile, product, preference=pref, community_trust=community_trust
        )
        product_id = str(product.get("product_id") or "")
        evidence = list(pref.evidence_ids)
        for factor in score.factors:
            evidence.append(factor)

        verdict, summary, explanation = self._decide(
            profile, product, pref, score, alternative=alternative, community_trust=community_trust
        )

        alt_id = None
        alt_name = None
        if verdict in {"alternative_available", "not_recommended", "too_expensive"} and alternative:
            alt_id = str(alternative.get("product_id") or "") or None
            alt_name = str(alternative.get("product_name") or "") or None
            if alt_id:
                evidence.append(f"alternative:{alt_id}")

        return BuyingAdvice(
            product_id=product_id,
            profile_id=profile.profile_id,
            verdict=verdict,
            label=VERDICT_LABELS[verdict],
            summary=summary,
            explanation=explanation,
            evidence=tuple(dict.fromkeys(evidence)),
            evidence_ids=pref.evidence_ids,
            personal_deal_score=score.personal_deal_score,
            alternative_product_id=alt_id,
            alternative_product_name=alt_name,
        )

    def _decide(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        pref: PreferenceScoreResult,
        score: PersonalDealScore,
        *,
        alternative: dict[str, Any] | None,
        community_trust: float | None,
    ) -> tuple[BuyingVerdict, str, str]:
        product_id = str(product.get("product_id") or "")
        product_name = str(product.get("product_name") or product_id)
        price = product.get("known_price")
        brand = str(product.get("brand") or "")
        direction = str(product.get("recent_price_direction") or "").lower()
        near_low = product.get("price_near_low")
        owned = set(profile.owned_products) | set(profile.accessories_owned)

        if product_id in owned:
            return (
                "upgrade_not_worthwhile",
                f"{product_name} is already in the owned / accessories list.",
                (
                    f"Profile {profile.display_name} already lists this product as owned. "
                    "Evidence does not support recommending a duplicate purchase."
                ),
            )

        if brand and brand.lower() in {b.lower() for b in profile.disliked_brands}:
            return (
                "not_recommended",
                f"{brand} is on the disliked brands list for this profile.",
                (
                    f"Brand affinity evidence shows {brand} is disliked by "
                    f"{profile.display_name}. PersonalDealScore={score.personal_deal_score}."
                ),
            )

        trust = community_trust if community_trust is not None else score.community_trust
        if trust < 0.35:
            return (
                "poor_community_trust",
                "Community trust signals are weak for this listing.",
                (
                    f"Community trust score {round(trust, 2)} is below the 0.35 threshold. "
                    "Advice stays evidence-based and does not invent positive sentiment."
                ),
            )

        if (
            profile.budget is not None
            and price is not None
            and float(price) > float(profile.budget) * 1.15
        ):
            return (
                "too_expensive",
                f"Known price exceeds budget ₱{profile.budget:,.0f} by more than 15%.",
                (
                    f"Budget fit={round(score.budget_fit, 2)}. Known price {price} vs budget "
                    f"{profile.budget} {profile.currency}. "
                    + (
                        f"Consider alternative {alternative.get('product_name')}."
                        if alternative
                        else "No in-budget alternative was supplied."
                    )
                ),
            )

        if direction == "down" and near_low is not True and score.personal_deal_score < 88:
            return (
                "price_likely_to_drop",
                "Recent price direction is down and the product is not near a known low.",
                (
                    "Catalog evidence shows recent_price_direction=down and price_near_low "
                    f"is not true. Waiting may improve value for {profile.display_name}."
                ),
            )

        if (
            (direction == "up" or (near_low is False and score.budget_fit < 0.55))
            and score.personal_deal_score < 70
        ):
            return (
                "worth_waiting",
                "Fit is moderate and price signals do not favor buying immediately.",
                (
                    f"PersonalDealScore={score.personal_deal_score}, budget_fit="
                    f"{round(score.budget_fit, 2)}. Evidence suggests waiting."
                ),
            )

        if alternative and score.personal_deal_score < 72 and pref.total_score < 0.55:
            return (
                "alternative_available",
                "A better personal fit exists in the ranked alternatives.",
                (
                    f"{product_name} scores PersonalDealScore={score.personal_deal_score}. "
                    f"Alternative {alternative.get('product_name')} better matches "
                    f"{profile.display_name} preferences."
                ),
            )

        if score.personal_deal_score >= 88 and score.budget_fit >= 0.7 and pref.total_score >= 0.65:
            return (
                "excellent_choice",
                f"Strong personal fit for {profile.display_name}.",
                (
                    f"PersonalDealScore={score.personal_deal_score} with preference_fit="
                    f"{round(score.preference_fit, 2)}, budget_fit={round(score.budget_fit, 2)}, "
                    f"brand_affinity={round(score.brand_affinity, 2)}."
                ),
            )

        if score.personal_deal_score >= 75 and score.budget_fit >= 0.55:
            return (
                "good_value",
                "Solid personalized value based on DealScore and preferences.",
                (
                    f"PersonalDealScore={score.personal_deal_score}. Global DealScore="
                    f"{score.global_deal_score}. Preference total={round(pref.total_score, 2)}."
                ),
            )

        if score.personal_deal_score < 55:
            return (
                "not_recommended",
                "Personal fit is weak given the available evidence.",
                (
                    f"PersonalDealScore={score.personal_deal_score} is below 55. "
                    "Recommendation withheld rather than fabricating affinity."
                ),
            )

        return (
            "good_value",
            "Acceptable fit with available evidence.",
            (
                f"PersonalDealScore={score.personal_deal_score}. Factors: "
                + "; ".join(score.factors[:4])
            ),
        )
