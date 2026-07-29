"""AI Shopping Assistant application service.

Combines DealBrain intelligence evidence with deterministic ranking and
optional multi-model narrative explanation. External AI remains disabled
unless server configuration explicitly enables it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.shopping_assistant import (
    AssistantWarning,
    ConversationTurn,
    ShoppingAssistantResponse,
    ShoppingEvidence,
    ShoppingQuery,
)
from app.domain.exceptions import ShoppingAssistantValidationError
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.intelligence.shopping_assistant.buy_now_wait import build_buy_now_or_wait
from app.intelligence.shopping_assistant.candidates import ProductCandidateService
from app.intelligence.shopping_assistant.comparison import ProductComparisonService
from app.intelligence.shopping_assistant.confidence import ConfidenceCalculator
from app.intelligence.shopping_assistant.evidence import ShoppingEvidenceService
from app.intelligence.shopping_assistant.fixtures import DEMO_QUERIES, get_catalog
from app.intelligence.shopping_assistant.intent import (
    ShoppingIntentService,
    contains_prompt_injection,
)
from app.intelligence.shopping_assistant.orchestrator import ShoppingAssistantOrchestrator
from app.intelligence.shopping_assistant.recommendation import ShoppingRecommendationRanker
from app.intelligence.shopping_assistant.validator import ShoppingResponseValidator

DEFAULT_MAX_QUERY_LENGTH = 500


class ShoppingAssistantService:
    """Evidence-first shopping Q&A orchestration."""

    def __init__(
        self,
        *,
        intent_service: ShoppingIntentService | None = None,
        candidate_service: ProductCandidateService | None = None,
        evidence_service: ShoppingEvidenceService | None = None,
        comparison_service: ProductComparisonService | None = None,
        recommendation_service: ShoppingRecommendationRanker | None = None,
        validator: ShoppingResponseValidator | None = None,
        orchestrator: ShoppingAssistantOrchestrator | None = None,
        conversation_repository: ConversationRepository | None = None,
        confidence_calculator: ConfidenceCalculator | None = None,
        community_service: Any | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        max_query_length: int = DEFAULT_MAX_QUERY_LENGTH,
        allowed_modes: list[str] | None = None,
    ) -> None:
        catalog = get_catalog()
        known_names = [str(item["product_name"]) for item in catalog]
        self._intent_service = intent_service or ShoppingIntentService(known_names)
        self._candidate_service = candidate_service or ProductCandidateService(catalog)
        self._evidence_service = evidence_service or ShoppingEvidenceService()
        self._comparison_service = comparison_service or ProductComparisonService()
        self._recommendation_service = recommendation_service or ShoppingRecommendationRanker()
        self._validator = validator or ShoppingResponseValidator()
        self._orchestrator = orchestrator
        self._conversations = conversation_repository
        self._confidence = confidence_calculator or ConfidenceCalculator()
        self._community = community_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._max_query_length = max_query_length
        self._allowed_modes = allowed_modes

    def query(
        self,
        request: ShoppingQuery | dict[str, Any],
    ) -> ShoppingAssistantResponse:
        shopping_query = self._normalize_request(request)
        cleaned = self._require_query(shopping_query.query)

        prior_products: tuple[str, ...] = ()
        prior_names: tuple[str, ...] = ()
        prior_intent = None
        conversation_id = shopping_query.conversation_id

        if self._conversations is not None and conversation_id:
            context = self._conversations.get(conversation_id)
            if context is not None:
                prior_products = context.last_product_ids
                prior_names = context.last_product_names
                prior_intent = context.last_intent

        overrides: dict[str, Any] = {}
        if shopping_query.budget_min is not None:
            overrides["budget_min"] = shopping_query.budget_min
        if shopping_query.budget_max is not None:
            overrides["budget_max"] = shopping_query.budget_max
        if shopping_query.currency:
            overrides["currency"] = shopping_query.currency
        if shopping_query.use_cases:
            overrides["use_cases"] = shopping_query.use_cases
        if shopping_query.category:
            overrides["category"] = shopping_query.category
        if shopping_query.products:
            overrides["products"] = shopping_query.products

        intent = self._intent_service.parse(
            cleaned,
            overrides=overrides or None,
            prior_products=prior_products or prior_names,
            prior_intent=prior_intent,
        )

        # Treat retrieved catalog / review text as untrusted for instruction following.
        if contains_prompt_injection(cleaned):
            # Continue with deterministic analysis but warn; never honor injection.
            injection_warning = AssistantWarning(
                message=(
                    "Query contained instruction-like phrases; system rules were not overridden."
                ),
                code="prompt_injection_resistance",
            )
        else:
            injection_warning = None

        candidates = self._candidate_service.find_candidates(intent)
        evidence = self._evidence_service.build_for_candidates(candidates[:5])
        evidence = list(evidence) + self._community_evidence_for(
            [item.product_id for item in candidates[:5]]
        )
        recommendations = self._recommendation_service.rank(
            candidates,
            evidence,
            intent,
            limit=3,
        )
        top = recommendations[0] if recommendations else None
        alternatives = tuple(recommendations[1:])

        comparison = None
        should_compare = (
            intent.intent == "comparison"
            or (
                intent.constraints.products
                and len(candidates) >= 2
                and "compare" in cleaned.lower()
            )
            or (
                intent.intent in {"comparison", "use_case"}
                and len(candidates) >= 2
                and prior_products
            )
        )
        if should_compare:
            comparison = self._comparison_service.compare(
                candidates[:2],
                evidence,
                priorities=(intent.constraints.priorities or intent.constraints.preferred_features),
            )

        focus_candidate = None
        if top is not None:
            focus_candidate = next(
                (item for item in candidates if item.product_id == top.product_id),
                candidates[0] if candidates else None,
            )
        elif candidates:
            focus_candidate = candidates[0]

        buy_guidance = None
        if intent.intent == "buy_now_or_wait" or "wait" in cleaned.lower():
            buy_guidance = build_buy_now_or_wait(focus_candidate, evidence)

        explanation_payload = {
            "intent": intent,
            "top": top,
            "alternatives": list(alternatives),
            "comparison": comparison,
            "candidates": candidates[:5],
            "buy_now_or_wait": buy_guidance,
            "structured": {
                "query": cleaned,
                "intent": intent.intent,
                "constraints": intent.constraints.to_dict(),
                "top": top.to_dict() if top else None,
                "alternatives": [item.to_dict() for item in alternatives],
                "evidence": [item.to_dict() for item in evidence],
                "comparison": comparison.to_dict() if comparison else None,
            },
        }

        mode = shopping_query.mode
        if self._orchestrator is not None:
            try:
                explained = self._orchestrator.explain(explanation_payload, mode=mode)
            except ValueError as exc:
                raise ShoppingAssistantValidationError(str(exc)) from exc
        else:
            from app.intelligence.shopping_assistant.deterministic import (
                DeterministicShoppingExplanationProvider,
            )

            explained = DeterministicShoppingExplanationProvider().explain(explanation_payload)
            explained.update(
                {
                    "mode": "economy",
                    "providers_used": ("deterministic",),
                    "fallback_used": True,
                    "fallback_reason": "orchestrator_not_configured",
                    "agreement_score": None,
                    "disagreements": (),
                }
            )

        confidence = self._confidence.calculate(
            candidates=candidates[:5],
            evidence=evidence,
            top=top,
            comparison=comparison,
            provider_agreement=explained.get("agreement_score"),
        )

        warnings: list[AssistantWarning] = [
            AssistantWarning(
                message=(
                    "Assistant answers use mock/imported DealBrain data and cannot guarantee "
                    "live prices, authenticity, or future price changes."
                ),
                code="limitations",
            )
        ]
        if injection_warning is not None:
            warnings.append(injection_warning)
        if not candidates:
            warnings.append(
                AssistantWarning(
                    message="No catalog candidates matched the extracted constraints.",
                    code="no_candidates",
                )
            )

        if conversation_id is None and self._conversations is not None:
            created = getattr(self._conversations, "create", None)
            conversation_id = created().conversation_id if callable(created) else self._id_factory()

        product_ids = tuple(item.product_id for item in candidates[:2])
        product_names = tuple(item.product_name for item in candidates[:2])
        if comparison is not None:
            product_ids = comparison.product_ids
            product_names = comparison.product_names
        elif top is not None:
            product_ids = (top.product_id,)
            product_names = (top.product_name,)

        if self._conversations is not None and conversation_id:
            now = self._clock()
            self._conversations.append_turn(
                conversation_id,
                ConversationTurn(
                    role="user",
                    intent=intent.intent,
                    product_ids=product_ids,
                    product_names=product_names,
                    query=cleaned,
                    created_at=now,
                ),
                last_intent=intent.intent,
                last_product_ids=product_ids,
                last_product_names=product_names,
                last_category=intent.constraints.category,
            )

        data_status = "mock"
        if candidates and all(item.data_status == "imported" for item in candidates[:3]):
            data_status = "imported"
        elif candidates and any(item.data_status == "live" for item in candidates[:3]):
            data_status = "live"

        response = ShoppingAssistantResponse(
            query=cleaned,
            intent=intent.intent,
            answer=str(explained.get("answer") or ""),
            top_recommendation=top,
            alternatives=alternatives,
            evidence=tuple(evidence),
            warnings=tuple(warnings),
            data_status=data_status,  # type: ignore[arg-type]
            providers_used=tuple(explained.get("providers_used") or ()),
            fallback_used=bool(explained.get("fallback_used")),
            confidence=confidence,
            mode=explained.get("mode") or "economy",
            comparison=comparison,
            conversation_id=conversation_id,
            disagreements=tuple(explained.get("disagreements") or ()),
            fallback_reason=explained.get("fallback_reason"),
            buy_now_or_wait=buy_guidance,
            processing={
                "parser": intent.parser,
                "allowed_modes": self.allowed_modes(),
                "secrets_included": False,
                "prompts_included": False,
                "candidate_count": len(candidates),
                "community_integrated": self._community is not None,
            },
            generated_at=self._clock(),
        )
        return self._validator.validate(response, evidence=evidence)

    def _community_evidence_for(self, product_ids: list[str]) -> list[ShoppingEvidence]:
        """Map provider-neutral community evidence into shopping evidence items."""
        if self._community is None or not product_ids:
            return []
        try:
            community_items = self._community.shopping_assistant_evidence(product_ids)
        except Exception:  # noqa: BLE001
            return []
        mapped: list[ShoppingEvidence] = []
        for item in community_items:
            mapped.append(
                ShoppingEvidence(
                    evidence_id=item.evidence_id,
                    type="community",
                    source_id="community_intelligence",
                    description=(
                        f"Community {item.topic}: {item.title or item.body[:120]} "
                        f"({item.sentiment.label})"
                    ),
                    product_id=item.product_id,
                    value=item.topic,
                )
            )
        return mapped

    def demo(self, *, mode: str | None = None) -> ShoppingAssistantResponse:
        return self.query(
            ShoppingQuery(
                query=DEMO_QUERIES[0],
                mode=mode,  # type: ignore[arg-type]
            )
        )

    def allowed_modes(self) -> list[str]:
        if self._allowed_modes is not None:
            return list(self._allowed_modes)
        if self._orchestrator is not None:
            return self._orchestrator.allowed_modes()
        return ["economy"]

    def _normalize_request(self, request: ShoppingQuery | dict[str, Any]) -> ShoppingQuery:
        if isinstance(request, ShoppingQuery):
            return request
        mode = request.get("mode")
        if mode is not None:
            mode = str(mode).strip().lower()
            if mode not in {"economy", "balanced", "maximum"}:
                raise ShoppingAssistantValidationError(
                    f"Unsupported mode: {request.get('mode')}. Use economy|balanced|maximum."
                )
            allowed = self.allowed_modes()
            if mode not in allowed:
                # Do not bypass server mode ceiling — clamp later via orchestrator.
                pass
        use_cases = request.get("use_cases") or []
        products = request.get("products") or []
        return ShoppingQuery(
            query=str(request.get("query") or ""),
            mode=mode,  # type: ignore[arg-type]
            conversation_id=request.get("conversation_id"),
            budget_min=request.get("budget_min"),
            budget_max=request.get("budget_max"),
            currency=request.get("currency"),
            use_cases=tuple(use_cases),
            category=request.get("category"),
            products=tuple(products),
        )

    def _require_query(self, query: str) -> str:
        cleaned = query.strip()
        if not cleaned:
            raise ShoppingAssistantValidationError("query must not be blank.")
        if len(cleaned) > self._max_query_length:
            raise ShoppingAssistantValidationError(
                f"query exceeds maximum length of {self._max_query_length} characters."
            )
        return cleaned
