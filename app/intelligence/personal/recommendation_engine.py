"""Personal recommendation engine — rank catalog products for a profile."""

from __future__ import annotations

from typing import Any

from app.domain.entities.personal_agent import (
    CustomerProfile,
    PersonalDealsResult,
    PersonalRecommendation,
)
from app.intelligence.personal.buying_advisor import BuyingAdvisor
from app.intelligence.personal.explanation_engine import ExplanationEngine
from app.intelligence.personal.preference_engine import PreferenceEngine
from app.intelligence.personal.scoring_engine import PersonalScoringEngine


class PersonalRecommendationEngine:
    """Rank products by PersonalDealScore and preference fit."""

    def __init__(
        self,
        *,
        preference_engine: PreferenceEngine | None = None,
        scoring_engine: PersonalScoringEngine | None = None,
        buying_advisor: BuyingAdvisor | None = None,
        explanation_engine: ExplanationEngine | None = None,
    ) -> None:
        self._preferences = preference_engine or PreferenceEngine()
        self._scoring = scoring_engine or PersonalScoringEngine(self._preferences)
        self._advisor = buying_advisor or BuyingAdvisor(
            preference_engine=self._preferences,
            scoring_engine=self._scoring,
        )
        self._explanations = explanation_engine or ExplanationEngine()

    def recommend(
        self,
        profile: CustomerProfile,
        products: list[dict[str, Any]],
        *,
        limit: int = 5,
        community_trust_by_product: dict[str, float] | None = None,
        knowledge_graph_by_product: dict[str, float] | None = None,
    ) -> PersonalDealsResult:
        community_trust_by_product = community_trust_by_product or {}
        knowledge_graph_by_product = knowledge_graph_by_product or {}
        scored: list[tuple[float, PersonalRecommendation]] = []

        # Pre-score all for alternative selection
        scored_products: list[tuple[float, dict[str, Any], Any, Any]] = []
        for product in products:
            pid = str(product.get("product_id") or "")
            pref = self._preferences.score(
                profile,
                product,
                community_sentiment=community_trust_by_product.get(pid),
                knowledge_graph_proximity=knowledge_graph_by_product.get(pid),
            )
            personal = self._scoring.score(
                profile,
                product,
                preference=pref,
                community_trust=community_trust_by_product.get(pid),
                knowledge_graph_proximity=knowledge_graph_by_product.get(pid),
            )
            scored_products.append((personal.personal_deal_score, product, pref, personal))

        scored_products.sort(key=lambda row: row[0], reverse=True)

        for _pds, product, pref, personal in scored_products[: max(limit * 2, 3)]:
            alternative = None
            if scored_products:
                # Best other product as alternative candidate
                for other in scored_products:
                    if other[1].get("product_id") != product.get("product_id"):
                        alternative = other[1]
                        break
            advice = self._advisor.advise(
                profile,
                product,
                preference=pref,
                personal_score=personal,
                alternative=alternative,
                community_trust=community_trust_by_product.get(
                    str(product.get("product_id") or "")
                ),
            )
            explanation = self._explanations.explain_recommendation(
                profile,
                product,
                preference=pref,
                personal_score=personal,
                advice=advice,
            )
            reason = self._explanations.reason_line(profile, product, personal, advice)
            rec = PersonalRecommendation(
                product_id=str(product.get("product_id") or ""),
                product_name=str(product.get("product_name") or ""),
                profile_id=profile.profile_id,
                reason=reason,
                explanation=explanation,
                known_price=product.get("known_price"),
                currency=str(product.get("currency") or profile.currency),
                marketplace=product.get("marketplace"),
                personal_deal_score=personal.personal_deal_score,
                global_deal_score=personal.global_deal_score,
                preference_score=pref.total_score,
                confidence=pref.confidence,
                advice=advice,
                evidence_ids=pref.evidence_ids,
                preference_dimensions=pref.dimensions,
                rating=product.get("rating"),
                review_count=int(product.get("review_count") or 0),
            )
            # Sort key: personal deal score, then preference, then global deal
            sort_key = (
                personal.personal_deal_score,
                pref.total_score,
                float(personal.global_deal_score or 0.0),
            )
            scored.append((sort_key[0] + sort_key[1] * 0.01, rec))

        scored.sort(key=lambda row: row[0], reverse=True)
        recommendations = tuple(item for _, item in scored[:limit])
        warnings: list[str] = []
        if not recommendations:
            warnings.append("No catalog products available for personalization.")

        return PersonalDealsResult(
            profile_id=profile.profile_id,
            recommendations=recommendations,
            data_status="mock",
            warnings=tuple(warnings),
            processing={
                "engine": "personal_recommendation_v1",
                "candidate_count": len(products),
                "limit": limit,
                "secrets_included": False,
            },
        )

    def recommend_one(
        self,
        profile: CustomerProfile,
        product: dict[str, Any],
        *,
        alternatives: list[dict[str, Any]] | None = None,
        community_trust: float | None = None,
        knowledge_graph_proximity: float | None = None,
    ) -> PersonalRecommendation:
        pool = [product, *(alternatives or [])]
        # Deduplicate by product_id preserving order
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in pool:
            pid = str(item.get("product_id") or "")
            if pid and pid not in seen:
                seen.add(pid)
                unique.append(item)
        result = self.recommend(
            profile,
            unique,
            limit=1,
            community_trust_by_product=(
                {str(product.get("product_id") or ""): community_trust}
                if community_trust is not None
                else None
            ),
            knowledge_graph_by_product=(
                {str(product.get("product_id") or ""): knowledge_graph_proximity}
                if knowledge_graph_proximity is not None
                else None
            ),
        )
        if result.recommendations:
            # Ensure the requested product is returned even if not top of multi-rank
            for rec in result.recommendations:
                if rec.product_id == str(product.get("product_id") or ""):
                    return rec
            # Re-score specifically for the requested product
        pref = self._preferences.score(
            profile,
            product,
            community_sentiment=community_trust,
            knowledge_graph_proximity=knowledge_graph_proximity,
        )
        personal = self._scoring.score(
            profile,
            product,
            preference=pref,
            community_trust=community_trust,
            knowledge_graph_proximity=knowledge_graph_proximity,
        )
        alt = None
        for item in alternatives or []:
            if item.get("product_id") != product.get("product_id"):
                alt = item
                break
        advice = self._advisor.advise(
            profile,
            product,
            preference=pref,
            personal_score=personal,
            alternative=alt,
            community_trust=community_trust,
        )
        return PersonalRecommendation(
            product_id=str(product.get("product_id") or ""),
            product_name=str(product.get("product_name") or ""),
            profile_id=profile.profile_id,
            reason=self._explanations.reason_line(profile, product, personal, advice),
            explanation=self._explanations.explain_recommendation(
                profile, product, preference=pref, personal_score=personal, advice=advice
            ),
            known_price=product.get("known_price"),
            currency=str(product.get("currency") or profile.currency),
            marketplace=product.get("marketplace"),
            personal_deal_score=personal.personal_deal_score,
            global_deal_score=personal.global_deal_score,
            preference_score=pref.total_score,
            confidence=pref.confidence,
            advice=advice,
            evidence_ids=pref.evidence_ids,
            preference_dimensions=pref.dimensions,
            rating=product.get("rating"),
            review_count=int(product.get("review_count") or 0),
        )
