"""Personal DealScore engine.

Composes global DealScore with preference fit, budget fit, brand affinity,
ownership compatibility, and community trust. Never invents missing signals —
neutral defaults are used when evidence is absent.
"""

from __future__ import annotations

from typing import Any

from app.domain.entities.personal_agent import (
    CustomerProfile,
    PersonalDealScore,
    PreferenceScoreResult,
)
from app.intelligence.personal.preference_engine import PreferenceEngine


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _dim(result: PreferenceScoreResult, name: str) -> float:
    for item in result.dimensions:
        if item.dimension == name:
            return item.score
    return 0.5


class PersonalScoringEngine:
    """Compute PersonalDealScore from catalog + preference scores."""

    def __init__(self, preference_engine: PreferenceEngine | None = None) -> None:
        self._preferences = preference_engine or PreferenceEngine()

    def score(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        *,
        preference: PreferenceScoreResult | None = None,
        community_trust: float | None = None,
        knowledge_graph_proximity: float | None = None,
    ) -> PersonalDealScore:
        pref = preference or self._preferences.score(
            profile,
            product,
            community_sentiment=community_trust,
            knowledge_graph_proximity=knowledge_graph_proximity,
        )
        global_deal = product.get("deal_score")
        global_norm = float(global_deal) / 100.0 if global_deal is not None else 0.5

        budget_fit = _dim(pref, "budget_fit")
        brand_affinity = _dim(pref, "brand_affinity")
        preference_fit = pref.total_score
        ownership = self._ownership_compatibility(profile, product)
        trust = (
            _clamp(float(community_trust), 0.0, 1.0)
            if community_trust is not None
            else _dim(pref, "community_sentiment")
        )

        # Weighted blend → 0–100 PersonalDealScore
        personal = 100.0 * (
            0.30 * global_norm
            + 0.22 * preference_fit
            + 0.18 * budget_fit
            + 0.12 * brand_affinity
            + 0.10 * ownership
            + 0.08 * trust
        )

        factors: list[str] = []
        if global_deal is not None:
            factors.append(f"global_deal_score={round(float(global_deal), 1)}")
        factors.append(f"preference_fit={round(preference_fit, 3)}")
        factors.append(f"budget_fit={round(budget_fit, 3)}")
        factors.append(f"brand_affinity={round(brand_affinity, 3)}")
        factors.append(f"ownership_compatibility={round(ownership, 3)}")
        factors.append(f"community_trust={round(trust, 3)}")

        return PersonalDealScore(
            product_id=str(product.get("product_id") or ""),
            profile_id=profile.profile_id,
            personal_deal_score=round(_clamp(personal), 2),
            global_deal_score=float(global_deal) if global_deal is not None else None,
            preference_fit=preference_fit,
            budget_fit=budget_fit,
            brand_affinity=brand_affinity,
            ownership_compatibility=ownership,
            community_trust=trust,
            factors=tuple(factors),
            evidence_ids=pref.evidence_ids,
        )

    def _ownership_compatibility(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> float:
        product_id = str(product.get("product_id") or "")
        brand = str(product.get("brand") or "").lower()
        owned = set(profile.owned_products) | set(profile.accessories_owned)
        wishlist = set(profile.wishlist)

        if product_id in owned:
            # Already owned — upgrade may not be worthwhile
            return 0.25
        if product_id in wishlist:
            return 0.95

        # Ecosystem bonus: owned Apple accessory + Apple product
        owned_blob = " ".join(owned).lower()
        if brand == "apple" and ("airpods" in owned_blob or "apple" in owned_blob):
            return 0.85
        if brand and brand in {b.lower() for b in profile.favorite_brands}:
            return 0.7
        if brand and brand in {b.lower() for b in profile.disliked_brands}:
            return 0.15
        return 0.55
