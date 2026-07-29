"""Preference engine — weighted, normalized preference scoring.

Never fabricates personalization: scores only use catalog attributes and
explicit profile fields (fixtures). Missing evidence yields neutral scores.
"""

from __future__ import annotations

from typing import Any

from app.domain.entities.personal_agent import (
    PREFERENCE_DIMENSIONS,
    CustomerProfile,
    PreferenceDimensionScore,
    PreferenceScoreResult,
)

# Default weights sum to 1.0
DEFAULT_WEIGHTS: dict[str, float] = {
    "budget_fit": 0.18,
    "brand_affinity": 0.14,
    "feature_match": 0.14,
    "marketplace_preference": 0.08,
    "community_sentiment": 0.08,
    "review_quality": 0.10,
    "knowledge_graph_proximity": 0.06,
    "availability": 0.06,
    "deal_score": 0.16,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


class PreferenceEngine:
    """Compute normalized weighted preference scores for a product vs profile."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        raw = dict(weights or DEFAULT_WEIGHTS)
        total = sum(raw.get(dim, 0.0) for dim in PREFERENCE_DIMENSIONS) or 1.0
        self._weights = {
            dim: float(raw.get(dim, 0.0)) / total for dim in PREFERENCE_DIMENSIONS
        }

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    def score(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        *,
        community_sentiment: float | None = None,
        knowledge_graph_proximity: float | None = None,
    ) -> PreferenceScoreResult:
        product_id = str(product.get("product_id") or "")
        dimensions: list[PreferenceDimensionScore] = []
        evidence_ids: list[str] = []

        scorers = {
            "budget_fit": self._budget_fit,
            "brand_affinity": self._brand_affinity,
            "feature_match": self._feature_match,
            "marketplace_preference": self._marketplace_preference,
            "community_sentiment": lambda p, prod: self._optional_score(
                community_sentiment,
                evidence=(
                    (f"community:{product_id}",)
                    if community_sentiment is not None
                    else ()
                ),
            ),
            "review_quality": self._review_quality,
            "knowledge_graph_proximity": lambda p, prod: self._optional_score(
                knowledge_graph_proximity,
                evidence=(
                    (f"graph:{product_id}",)
                    if knowledge_graph_proximity is not None
                    else ()
                ),
            ),
            "availability": self._availability,
            "deal_score": self._deal_score,
        }

        for dimension in PREFERENCE_DIMENSIONS:
            score, evidence = scorers[dimension](profile, product)
            weight = self._weights[dimension]
            dimensions.append(
                PreferenceDimensionScore(
                    dimension=dimension,
                    score=_clamp01(score),
                    weight=weight,
                    weighted_score=_clamp01(score) * weight,
                    evidence=evidence,
                )
            )
            evidence_ids.extend(evidence)

        total = sum(item.weighted_score for item in dimensions)
        confidence = _clamp01(0.4 + 0.6 * total)
        return PreferenceScoreResult(
            profile_id=profile.profile_id,
            product_id=product_id,
            total_score=_clamp01(total),
            dimensions=tuple(dimensions),
            confidence=confidence,
            confidence_band=_band(confidence),  # type: ignore[arg-type]
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        )

    def _budget_fit(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        price = product.get("known_price")
        budget = profile.budget
        product_id = str(product.get("product_id") or "")
        if price is None or budget is None or budget <= 0:
            return 0.5, ()
        price_f = float(price)
        if price_f <= budget:
            # Prefer headroom when price-sensitive.
            ratio = price_f / budget
            score = 1.0 - (ratio * 0.35 * profile.price_sensitivity)
            return _clamp01(score), (f"budget:{product_id}",)
        overshoot = (price_f - budget) / budget
        score = max(0.0, 0.45 - overshoot * (0.7 + 0.3 * profile.price_sensitivity))
        return _clamp01(score), (f"budget:{product_id}",)

    def _brand_affinity(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        brand = str(product.get("brand") or "").strip()
        product_id = str(product.get("product_id") or "")
        if not brand:
            return 0.5, ()
        brand_l = brand.lower()
        favorites = {b.lower() for b in profile.favorite_brands}
        disliked = {b.lower() for b in profile.disliked_brands}
        if brand_l in disliked:
            return 0.05, (f"brand_dislike:{product_id}",)
        if brand_l in favorites:
            return 1.0, (f"brand_like:{product_id}",)
        return 0.45, ()

    def _feature_match(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        product_id = str(product.get("product_id") or "")
        use_cases = {str(u).lower() for u in (product.get("use_cases") or ())}
        features = {str(f).lower() for f in (product.get("features") or ())}
        strengths = {str(s).lower() for s in (product.get("strengths") or ())}
        blob = " ".join(use_cases | features | strengths)

        hits = 0.0
        checks = 0.0

        def check(condition: bool, weight: float = 1.0) -> None:
            nonlocal hits, checks
            checks += weight
            if condition:
                hits += weight

        check(profile.gaming and ("gaming" in use_cases or "rtx" in blob), 1.2)
        check(profile.office_work and ("productivity" in use_cases or "office" in blob))
        check(profile.student and ("student" in use_cases or profile.budget is not None))
        check(
            profile.creator
            and ("content_creation" in use_cases or "photo" in blob or "editing" in blob),
            1.1,
        )
        check(profile.traveler and ("travel" in use_cases or "battery" in blob or "light" in blob))
        check(profile.battery_priority >= 0.7 and ("battery" in blob or "fanless" in blob), 1.0)
        check(
            profile.performance_priority >= 0.7
            and ("rtx" in blob or "performance" in blob or "mux" in blob),
            1.0,
        )
        check(profile.camera_priority >= 0.7 and ("camera" in blob or "photo" in blob), 1.2)
        check(profile.storage_priority >= 0.7 and ("512" in blob or "storage" in blob), 0.8)

        category = str(product.get("category") or "").lower()
        if profile.favorite_categories:
            check(category in {c.lower() for c in profile.favorite_categories}, 1.0)

        if checks <= 0:
            return 0.5, ()
        return _clamp01(hits / checks), (f"features:{product_id}",)

    def _marketplace_preference(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        marketplace = str(product.get("marketplace") or "").strip()
        product_id = str(product.get("product_id") or "")
        if not marketplace or not profile.preferred_marketplaces:
            return 0.5, ()
        preferred = {m.lower() for m in profile.preferred_marketplaces}
        if marketplace.lower() in preferred:
            return 1.0, (f"marketplace:{product_id}",)
        return 0.35, (f"marketplace:{product_id}",)

    def _review_quality(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        product_id = str(product.get("product_id") or "")
        rating = product.get("rating")
        count = int(product.get("review_count") or 0)
        if rating is None:
            return 0.5, ()
        rating_score = _clamp01(float(rating) / 5.0)
        volume = _clamp01(count / 5000.0)
        score = 0.7 * rating_score + 0.3 * volume
        return score, (f"reviews:{product_id}",)

    def _availability(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        product_id = str(product.get("product_id") or "")
        # Fixture catalog assumes available listings; boost near-low price.
        near_low = product.get("price_near_low")
        if near_low is True:
            return 0.9, (f"availability:{product_id}",)
        if near_low is False:
            return 0.65, (f"availability:{product_id}",)
        return 0.7, ()

    def _deal_score(
        self, profile: CustomerProfile, product: dict[str, Any]
    ) -> tuple[float, tuple[str, ...]]:
        product_id = str(product.get("product_id") or "")
        deal = product.get("deal_score")
        if deal is None:
            return 0.5, ()
        return _clamp01(float(deal) / 100.0), (f"dealscore:{product_id}",)

    def _optional_score(
        self,
        value: float | None,
        *,
        evidence: tuple[str, ...] = (),
    ) -> tuple[float, tuple[str, ...]]:
        if value is None:
            return 0.5, ()
        return _clamp01(float(value)), evidence
