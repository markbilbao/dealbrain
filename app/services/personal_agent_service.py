"""Personal AI Shopping Agent application service facade."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.personal_agent import (
    BuyingAdvice,
    CustomerProfile,
    PersonalDealScore,
    PersonalDealsResult,
    PersonalDemoPayload,
    PersonalRecommendation,
    PreferenceScoreResult,
)
from app.domain.exceptions import PersonalAgentNotFoundError, PersonalAgentValidationError
from app.intelligence.personal.buying_advisor import BuyingAdvisor
from app.intelligence.personal.explanation_engine import ExplanationEngine
from app.intelligence.personal.fixtures import LIMITATIONS, catalog_product_map
from app.intelligence.personal.preference_engine import PreferenceEngine
from app.intelligence.personal.profile_manager import ProfileManager
from app.intelligence.personal.recommendation_engine import PersonalRecommendationEngine
from app.intelligence.personal.scoring_engine import PersonalScoringEngine
from app.intelligence.shopping_assistant.fixtures import get_catalog as get_shopping_catalog
from app.intelligence.shopping_assistant.fixtures import get_product_by_id


class PersonalAgentService:
    """Application facade for profile-driven personalization."""

    def __init__(
        self,
        *,
        profile_manager: ProfileManager | None = None,
        preference_engine: PreferenceEngine | None = None,
        scoring_engine: PersonalScoringEngine | None = None,
        recommendation_engine: PersonalRecommendationEngine | None = None,
        buying_advisor: BuyingAdvisor | None = None,
        explanation_engine: ExplanationEngine | None = None,
        enabled: bool = True,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        community_service: Any | None = None,
        knowledge_graph_service: Any | None = None,
    ) -> None:
        self._profiles = profile_manager or ProfileManager()
        self._preferences = preference_engine or PreferenceEngine()
        self._scoring = scoring_engine or PersonalScoringEngine(self._preferences)
        self._explanations = explanation_engine or ExplanationEngine()
        self._advisor = buying_advisor or BuyingAdvisor(
            preference_engine=self._preferences,
            scoring_engine=self._scoring,
        )
        self._recommendations = recommendation_engine or PersonalRecommendationEngine(
            preference_engine=self._preferences,
            scoring_engine=self._scoring,
            buying_advisor=self._advisor,
            explanation_engine=self._explanations,
        )
        self._enabled = enabled
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._community = community_service
        self._knowledge_graph = knowledge_graph_service

    @property
    def enabled(self) -> bool:
        return self._enabled

    def demo(self, *, profile_id: str | None = None) -> PersonalDemoPayload:
        self._require_enabled()
        if profile_id:
            profile = self._profiles.set_active(profile_id)
        else:
            profile = self._profiles.get_active()
        deals = self.deals(profile_id=profile.profile_id, limit=5)
        return PersonalDemoPayload(
            active_profile=profile,
            profiles=tuple(self._profiles.list_profiles()),
            deals=deals,
            limitations=LIMITATIONS,
        )

    def list_profiles(self) -> list[CustomerProfile]:
        self._require_enabled()
        return self._profiles.list_profiles()

    def get_profile(self, profile_id: str | None = None) -> CustomerProfile:
        self._require_enabled()
        return self._profiles.get_profile(profile_id)

    def set_active_profile(self, profile_id: str) -> CustomerProfile:
        self._require_enabled()
        return self._profiles.set_active(profile_id)

    def preference_score(
        self, product_id: str, *, profile_id: str | None = None
    ) -> PreferenceScoreResult:
        self._require_enabled()
        profile = self._profiles.get_profile(profile_id)
        product = self._require_product(product_id)
        return self._preferences.score(
            profile,
            product,
            community_sentiment=self._community_trust(product_id),
            knowledge_graph_proximity=self._graph_proximity(product_id),
        )

    def personal_deal_score(
        self, product_id: str, *, profile_id: str | None = None
    ) -> PersonalDealScore:
        self._require_enabled()
        profile = self._profiles.get_profile(profile_id)
        product = self._require_product(product_id)
        return self._scoring.score(
            profile,
            product,
            community_trust=self._community_trust(product_id),
            knowledge_graph_proximity=self._graph_proximity(product_id),
        )

    def recommendation(
        self, product_id: str, *, profile_id: str | None = None
    ) -> PersonalRecommendation:
        self._require_enabled()
        profile = self._profiles.get_profile(profile_id)
        product = self._require_product(product_id)
        alternatives = [
            item
            for item in get_shopping_catalog()
            if item.get("product_id") != product_id
            and item.get("category") == product.get("category")
        ][:4]
        return self._recommendations.recommend_one(
            profile,
            product,
            alternatives=alternatives,
            community_trust=self._community_trust(product_id),
            knowledge_graph_proximity=self._graph_proximity(product_id),
        )

    def deals(self, *, profile_id: str | None = None, limit: int = 5) -> PersonalDealsResult:
        self._require_enabled()
        if limit < 1 or limit > 20:
            raise PersonalAgentValidationError("limit must be between 1 and 20.")
        profile = self._profiles.get_profile(profile_id)
        products = get_shopping_catalog()
        trust_map = {
            str(item["product_id"]): trust
            for item in products
            if (trust := self._community_trust(str(item["product_id"]))) is not None
        }
        graph_map = {
            str(item["product_id"]): prox
            for item in products
            if (prox := self._graph_proximity(str(item["product_id"]))) is not None
        }
        result = self._recommendations.recommend(
            profile,
            products,
            limit=limit,
            community_trust_by_product=trust_map or None,
            knowledge_graph_by_product=graph_map or None,
        )
        return PersonalDealsResult(
            profile_id=result.profile_id,
            recommendations=result.recommendations,
            data_status=result.data_status,
            warnings=result.warnings,
            generated_at=self._clock(),
            processing={
                **result.processing,
                "personal_agent_enabled": self._enabled,
                "community_integrated": self._community is not None,
                "knowledge_graph_integrated": self._knowledge_graph is not None,
            },
        )

    def advice(self, product_id: str, *, profile_id: str | None = None) -> BuyingAdvice:
        self._require_enabled()
        profile = self._profiles.get_profile(profile_id)
        product = self._require_product(product_id)
        alternatives = [
            item
            for item in get_shopping_catalog()
            if item.get("product_id") != product_id
        ]
        # Prefer best alternative by personal score for same category
        alt = None
        same_cat = [a for a in alternatives if a.get("category") == product.get("category")]
        pool = same_cat or alternatives
        if pool:
            ranked = self._recommendations.recommend(profile, pool, limit=1)
            if ranked.recommendations:
                alt = get_product_by_id(ranked.recommendations[0].product_id)
        return self._advisor.advise(
            profile,
            product,
            alternative=alt,
            community_trust=self._community_trust(product_id),
        )

    def shopping_assistant_overrides(self, profile_id: str | None) -> dict[str, Any]:
        """Intent overrides for Shopping Assistant when a profile is present."""
        if not self._enabled or not profile_id:
            return {}
        try:
            profile = self._profiles.get_profile(profile_id)
        except (PersonalAgentNotFoundError, PersonalAgentValidationError):
            return {}
        return self._profiles.intent_overrides(profile)

    def shopping_assistant_personalize(
        self,
        *,
        profile_id: str | None,
        product_ids: list[str],
    ) -> dict[str, Any] | None:
        """Build personal recommendation payload for Shopping Assistant integration."""
        if not self._enabled or not profile_id:
            return None
        try:
            profile = self._profiles.get_profile(profile_id)
        except (PersonalAgentNotFoundError, PersonalAgentValidationError):
            return None
        if not product_ids:
            deals = self.deals(profile_id=profile.profile_id, limit=3)
            top = deals.recommendations[0] if deals.recommendations else None
        else:
            top = self.recommendation(product_ids[0], profile_id=profile.profile_id)
        if top is None:
            return None
        return {
            "profile_id": profile.profile_id,
            "profile_name": profile.display_name,
            "persona": profile.persona,
            "recommendation": top.to_dict(),
            "personal_deal_score": top.personal_deal_score,
            "advice": top.advice.to_dict() if top.advice else None,
            "mode": "personal",
        }

    def shopping_assistant_evidence(self, product_ids: list[str], *, profile_id: str | None = None):
        """Map personalization signals into shopping-assistant-shaped evidence dicts."""
        if not self._enabled or not product_ids or not profile_id:
            return []
        try:
            profile = self._profiles.get_profile(profile_id)
        except (PersonalAgentNotFoundError, PersonalAgentValidationError):
            return []
        items: list[dict[str, Any]] = []
        for product_id in product_ids[:5]:
            product = get_product_by_id(product_id)
            if product is None:
                continue
            score = self._scoring.score(
                profile,
                product,
                community_trust=self._community_trust(product_id),
                knowledge_graph_proximity=self._graph_proximity(product_id),
            )
            items.append(
                {
                    "evidence_id": f"personal-{profile.profile_id}-{product_id}",
                    "type": "recommendation",
                    "description": (
                        f"PersonalDealScore {score.personal_deal_score} for "
                        f"{profile.display_name} "
                        f"(budget_fit={round(score.budget_fit, 2)}, "
                        f"brand_affinity={round(score.brand_affinity, 2)})"
                    ),
                    "product_id": product_id,
                    "value": score.personal_deal_score,
                }
            )
        return items

    def meta(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "default_profile_id": self._profiles.get_active().profile_id,
            "profile_count": len(self._profiles.list_profiles()),
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "display_name": p.display_name,
                    "persona": p.persona,
                }
                for p in self._profiles.list_profiles()
            ],
            "data_status": "mock",
            "authentication": False,
            "cloud_sync": False,
            "limitations": list(LIMITATIONS),
            "preference_dimensions": list(self._preferences.weights.keys()),
        }

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise PersonalAgentValidationError("Personal shopping agent is disabled.")

    def _require_product(self, product_id: str) -> dict[str, Any]:
        cleaned = product_id.strip()
        if not cleaned:
            raise PersonalAgentValidationError("product_id must not be blank.")
        product = get_product_by_id(cleaned)
        if product is None:
            # Also allow map lookup for completeness
            product = catalog_product_map().get(cleaned)
        if product is None:
            raise PersonalAgentNotFoundError(cleaned)
        return product

    def _community_trust(self, product_id: str) -> float | None:
        if self._community is None:
            return None
        try:
            if hasattr(self._community, "product_trust"):
                trust = self._community.product_trust(product_id)
                if isinstance(trust, (int, float)):
                    return float(trust)
            if hasattr(self._community, "shopping_assistant_evidence"):
                items = self._community.shopping_assistant_evidence([product_id])
                if not items:
                    return 0.55
                # Soft signal from presence of community evidence
                return 0.7
        except Exception:  # noqa: BLE001
            return None
        return None

    def _graph_proximity(self, product_id: str) -> float | None:
        if self._knowledge_graph is None:
            return None
        try:
            if hasattr(self._knowledge_graph, "shopping_assistant_evidence"):
                items = self._knowledge_graph.shopping_assistant_evidence([product_id])
                if not items:
                    return 0.5
                return min(1.0, 0.55 + 0.1 * len(items))
        except Exception:  # noqa: BLE001
            return None
        return None
