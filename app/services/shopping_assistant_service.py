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
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
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
from app.services.answer_from_evidence import AnswerFromEvidenceService

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
        snapshot_repository: DecisionSnapshotRepository | None = None,
        confidence_calculator: ConfidenceCalculator | None = None,
        community_service: Any | None = None,
        knowledge_graph_service: Any | None = None,
        personal_agent_service: Any | None = None,
        user_platform_service: Any | None = None,
        marketplace_data_service: Any | None = None,
        # Sprint 19 additions — Watchlists/Alerts/Notification Center
        # collaborators, all optional and duck-typed to avoid import cycles.
        # Anonymous callers (no user_id) only ever get informational reads
        # through these; every persistent write path below requires an
        # authenticated user_id.
        watchlist_service: Any | None = None,
        alert_rule_service: Any | None = None,
        notification_center_service: Any | None = None,
        alert_evaluation_service: Any | None = None,
        # Sprint 20 — Affiliate link generation AFTER recommendation selection.
        # Never consulted during ranking / DealScore. Optional collaborator.
        affiliate_link_service: Any | None = None,
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
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._evidence_answers = AnswerFromEvidenceService(
            snapshots=snapshot_repository,
            conversations=conversation_repository,
            clock=self._clock,
            id_factory=self._id_factory,
        )
        self._confidence = confidence_calculator or ConfidenceCalculator()
        self._community = community_service
        self._knowledge_graph = knowledge_graph_service
        self._personal_agent = personal_agent_service
        self._user_platform = user_platform_service
        self._marketplace_data = marketplace_data_service
        self._watchlist_service = watchlist_service
        self._alert_rule_service = alert_rule_service
        self._notification_center = notification_center_service
        self._alert_evaluation_service = alert_evaluation_service
        self._affiliate_link_service = affiliate_link_service
        self._max_query_length = max_query_length
        self._allowed_modes = allowed_modes

    def query(
        self,
        request: ShoppingQuery | dict[str, Any],
        *,
        location: Any | None = None,
    ) -> ShoppingAssistantResponse:
        if isinstance(request, dict) and request.get("decision_id"):
            cleaned = self._require_query(str(request.get("query") or ""))
            payload = dict(request)
            payload["query"] = cleaned
            return self._evidence_answers.answer(payload, location=location)
        if isinstance(request, ShoppingQuery) and request.decision_id:
            cleaned = self._require_query(request.query)
            payload = request.to_dict()
            payload["query"] = cleaned
            return self._evidence_answers.answer(payload, location=location)
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

        # User platform (authenticated account) overrides fill gaps first; personal
        # profile overrides may then refine further. Explicit query fields always win.
        user_platform_context = self._user_platform_context(shopping_query.user_id)
        user_platform_overrides = dict(user_platform_context.get("overrides") or {})
        for key, value in user_platform_overrides.items():
            if key == "profile_id":
                continue
            if key not in overrides or overrides[key] in (None, (), [], ""):
                overrides[key] = value

        # Authenticated accounts may link a Personal AI fixture profile when the
        # personal agent collaborator is available.
        effective_profile_id = shopping_query.profile_id
        if not effective_profile_id and self._personal_agent is not None:
            effective_profile_id = user_platform_context.get(
                "personal_profile_id"
            ) or user_platform_overrides.get("profile_id")

        # Profile overrides fill gaps only — explicit query fields win.
        profile_overrides = self._personal_overrides(effective_profile_id)
        for key, value in profile_overrides.items():
            if key not in overrides or overrides[key] in (None, (), [], ""):
                overrides[key] = value

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
        candidates, marketplace_warnings = self._apply_marketplace_data_provenance(candidates)
        evidence = self._evidence_service.build_for_candidates(candidates[:5])
        evidence = list(evidence) + self._community_evidence_for(
            [item.product_id for item in candidates[:5]]
        )
        evidence = list(evidence) + self._graph_evidence_for(
            [item.product_id for item in candidates[:5]]
        )
        evidence = list(evidence) + self._personal_evidence_for(
            [item.product_id for item in candidates[:5]],
            profile_id=effective_profile_id,
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
                    "Assistant answers use mock/imported PiqSavi data and cannot guarantee "
                    "live prices, authenticity, or future price changes."
                ),
                code="limitations",
            )
        ]
        if injection_warning is not None:
            warnings.append(injection_warning)
        warnings.extend(marketplace_warnings)
        if not candidates:
            warnings.append(
                AssistantWarning(
                    message="No catalog candidates matched the extracted constraints.",
                    code="no_candidates",
                )
            )
        if self._knowledge_graph is None:
            warnings.append(
                AssistantWarning(
                    message=(
                        "Knowledge graph evidence was unavailable; used existing assistant flow."
                    ),
                    code="graph_unavailable",
                )
            )

        personal_payload = self._personal_recommendation_payload(
            effective_profile_id,
            [item.product_id for item in candidates[:3]],
        )
        if effective_profile_id and personal_payload is None and self._personal_agent is None:
            warnings.append(
                AssistantWarning(
                    message=(
                        "Personal profile was requested but the personal agent was unavailable; "
                        "fell back to generic recommendations."
                    ),
                    code="personal_profile_unavailable",
                )
            )
        elif effective_profile_id and personal_payload is None:
            warnings.append(
                AssistantWarning(
                    message=("Requested profile could not be applied; fell back to generic mode."),
                    code="personal_profile_unavailable",
                )
            )

        if shopping_query.user_id and not user_platform_context.get("authenticated"):
            warnings.append(
                AssistantWarning(
                    message=(
                        "A user account was referenced but could not be authenticated; "
                        "fell back to anonymous personalization."
                    ),
                    code="user_platform_unavailable",
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

        if self._user_platform is not None and shopping_query.user_id:
            self._record_user_platform_history(
                shopping_query.user_id,
                query=cleaned,
                summary=str(explained.get("answer") or ""),
                product_ids=product_ids,
                profile_id=effective_profile_id,
            )

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

        # Prefer personalized top recommendation when profile personalization succeeded.
        if personal_payload and personal_payload.get("recommendation"):
            personal_rec = personal_payload["recommendation"]
            # Re-order generic top if personal agent ranked a different product higher
            # among candidates — keep evidence-grounded SA ranking unless personal top
            # is among candidates.
            personal_pid = personal_rec.get("product_id")
            if personal_pid and top is not None and personal_pid != top.product_id:
                match = next(
                    (item for item in recommendations if item.product_id == personal_pid),
                    None,
                )
                if match is not None:
                    alternatives = tuple(
                        [top] + [item for item in alternatives if item.product_id != personal_pid]
                    )[:2]
                    top = match
                    answer_prefix = (
                        f"Personal recommendation for {personal_payload.get('profile_name')}: "
                    )
                    explained = dict(explained)
                    explained["answer"] = answer_prefix + str(explained.get("answer") or "")

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
                "knowledge_graph_integrated": self._knowledge_graph is not None,
                "personal_agent_integrated": self._personal_agent is not None,
                "user_platform_integrated": self._user_platform is not None,
                "authenticated": bool(user_platform_context.get("authenticated")),
                "personalization_mode": (
                    "personal"
                    if personal_payload
                    else (
                        "authenticated" if user_platform_context.get("authenticated") else "generic"
                    )
                ),
                "profile_id": (
                    personal_payload.get("profile_id") if personal_payload else effective_profile_id
                ),
                "affiliate_integrated": self._affiliate_link_service is not None,
            },
            generated_at=self._clock(),
            personal_recommendation=personal_payload,
            profile_id=(
                personal_payload.get("profile_id") if personal_payload else effective_profile_id
            ),
        )
        # Sprint 20: affiliate link generation happens ONLY after the top
        # recommendation has already been selected. Commission never feeds
        # DealScore or the ranking key above.
        response = self._attach_affiliate_links(
            response,
            user_id=shopping_query.user_id,
            country=intent.constraints.location,
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

    def _graph_evidence_for(self, product_ids: list[str]) -> list[ShoppingEvidence]:
        """Map knowledge-graph evidence into shopping evidence items."""
        if self._knowledge_graph is None or not product_ids:
            return []
        try:
            graph_items = self._knowledge_graph.shopping_assistant_evidence(product_ids)
        except Exception:  # noqa: BLE001
            return []
        mapped: list[ShoppingEvidence] = []
        for item in graph_items:
            evidence_type = str(item.get("type") or "graph_path")
            if evidence_type not in {
                "graph_path",
                "related_product",
                "cross_source_support",
                "contradiction",
                "compatibility",
                "community_topic",
            }:
                evidence_type = "graph_path"
            mapped.append(
                ShoppingEvidence(
                    evidence_id=str(item.get("evidence_id") or self._id_factory()),
                    type=evidence_type,  # type: ignore[arg-type]
                    source_id="knowledge_graph",
                    description=str(item.get("description") or "Knowledge graph evidence"),
                    product_id=item.get("product_id"),
                    value=item.get("value"),
                )
            )
        return mapped

    def _personal_overrides(self, profile_id: str | None) -> dict[str, Any]:
        if self._personal_agent is None:
            return {}
        try:
            return dict(self._personal_agent.shopping_assistant_overrides(profile_id) or {})
        except Exception:  # noqa: BLE001
            return {}

    def _personal_evidence_for(
        self,
        product_ids: list[str],
        *,
        profile_id: str | None,
    ) -> list[ShoppingEvidence]:
        if self._personal_agent is None or not product_ids:
            return []
        try:
            items = self._personal_agent.shopping_assistant_evidence(
                product_ids, profile_id=profile_id
            )
        except Exception:  # noqa: BLE001
            return []
        mapped: list[ShoppingEvidence] = []
        for item in items:
            mapped.append(
                ShoppingEvidence(
                    evidence_id=str(item.get("evidence_id") or self._id_factory()),
                    type="recommendation",
                    source_id="personal_agent",
                    description=str(item.get("description") or "Personal preference evidence"),
                    product_id=item.get("product_id"),
                    value=item.get("value"),
                )
            )
        return mapped

    def _personal_recommendation_payload(
        self,
        profile_id: str | None,
        product_ids: list[str],
    ) -> dict[str, Any] | None:
        if self._personal_agent is None:
            return None
        try:
            return self._personal_agent.shopping_assistant_personalize(
                profile_id=profile_id,
                product_ids=product_ids,
            )
        except Exception:  # noqa: BLE001
            return None

    def _user_platform_context(self, user_id: str | None) -> dict[str, Any]:
        """Return authenticated-account personalization context, or {} when unavailable."""
        if self._user_platform is None or not user_id:
            return {}
        try:
            return dict(self._user_platform.shopping_assistant_context(user_id) or {})
        except Exception:  # noqa: BLE001
            return {}

    def _apply_marketplace_data_provenance(
        self, candidates: list[Any]
    ) -> tuple[list[Any], list[AssistantWarning]]:
        """Attach source-mode / freshness labels without excluding non-live offers."""
        from app.domain.entities.shopping_assistant import ShoppingCandidate

        warnings: list[AssistantWarning] = []
        if self._marketplace_data is None or not candidates:
            return candidates, warnings
        try:
            enrichments = self._marketplace_data.shopping_enrichment()
        except Exception:  # noqa: BLE001
            return candidates, warnings
        if not enrichments:
            return candidates, warnings

        by_title: dict[str, dict[str, Any]] = {}
        for item in enrichments:
            key = str(item.get("title") or "").strip().lower()
            if key and key not in by_title:
                by_title[key] = item

        updated: list[Any] = []
        seen_warnings: set[str] = set()
        for candidate in candidates:
            match = by_title.get(candidate.product_name.strip().lower())
            if match is None:
                for title, item in by_title.items():
                    name = candidate.product_name.lower()
                    if title in name or name in title:
                        match = item
                        break
            if match is None:
                updated.append(candidate)
                continue

            data_status = match.get("data_status") or candidate.data_status
            freshness_warning = match.get("freshness_warning")
            notes = list(match.get("notes") or [])
            boost = 0.0
            if data_status == "live" and match.get("is_current_live_price"):
                boost = 0.15
            elif data_status == "live":
                boost = 0.08
            elif data_status == "imported":
                boost = 0.03

            updated.append(
                ShoppingCandidate(
                    product_id=candidate.product_id,
                    product_name=candidate.product_name,
                    category=candidate.category,
                    known_price=candidate.known_price,
                    currency=candidate.currency,
                    marketplace=candidate.marketplace,
                    deal_score=candidate.deal_score,
                    rating=candidate.rating,
                    review_count=candidate.review_count,
                    brand=candidate.brand,
                    use_cases=candidate.use_cases,
                    features=candidate.features,
                    seller_name=candidate.seller_name,
                    seller_trust_score=candidate.seller_trust_score,
                    price_near_low=candidate.price_near_low,
                    recent_price_direction=candidate.recent_price_direction,
                    complaints=candidate.complaints,
                    strengths=candidate.strengths,
                    data_status=data_status,  # type: ignore[arg-type]
                    match_score=float(candidate.match_score) + boost,
                )
            )
            for note in notes[:2]:
                if note and note not in seen_warnings:
                    seen_warnings.add(note)
                    warnings.append(
                        AssistantWarning(message=str(note), code="marketplace_data_provenance")
                    )
            if freshness_warning and freshness_warning not in seen_warnings:
                seen_warnings.add(freshness_warning)
                warnings.append(
                    AssistantWarning(
                        message=str(freshness_warning),
                        code="marketplace_data_freshness",
                    )
                )
            if data_status != "live" or not match.get("is_current_live_price"):
                msg = (
                    "Never claim a price is currently available unless "
                    "supported by fresh live data."
                )
                if msg not in seen_warnings:
                    seen_warnings.add(msg)
                    warnings.append(AssistantWarning(message=msg, code="non_live_price_claim"))
        return updated, warnings

    def _record_user_platform_history(
        self,
        user_id: str,
        *,
        query: str,
        summary: str,
        product_ids: tuple[str, ...],
        profile_id: str | None,
    ) -> None:
        """Best-effort recommendation history recording — never raises."""
        try:
            self._user_platform.record_shopping_recommendation(
                user_id,
                query=query,
                summary=summary,
                product_ids=product_ids,
                profile_id=profile_id,
            )
        except Exception:  # noqa: BLE001
            return

    # ---------------------------------------------------------- Sprint 19: watchlists/alerts
    def _attach_affiliate_links(
        self,
        response: ShoppingAssistantResponse,
        *,
        user_id: str | None = None,
        country: str | None = None,
    ) -> ShoppingAssistantResponse:
        """Attach affiliate links AFTER recommendation selection.

        Never mutates DealScore, never reorders recommendations, never consults
        commission for ranking. Failures degrade to no affiliate payload.
        """
        if self._affiliate_link_service is None:
            return response

        generate = getattr(self._affiliate_link_service, "generate_for_recommendation", None)
        if not callable(generate):
            return response

        affiliate_payload: dict[str, Any] = {
            "applied_after_ranking": True,
            "dealscore_independent": True,
            "simulated": True,
            "top_link": None,
            "alternative_links": [],
            "disclaimer": (
                "Affiliate links are generated after recommendation selection. "
                "Commission never changes PiqScore or ranking."
            ),
        }
        try:
            top_link = generate(
                response.top_recommendation,
                campaign_id="shopping-assistant",
                user_id=user_id,
                country=country,
            )
            if top_link is not None:
                affiliate_payload["top_link"] = (
                    top_link.to_dict() if hasattr(top_link, "to_dict") else dict(top_link)
                )
            alt_links: list[dict[str, Any]] = []
            for alt in response.alternatives[:2]:
                link = generate(
                    alt,
                    campaign_id="shopping-assistant",
                    user_id=user_id,
                    country=country,
                )
                if link is not None:
                    alt_links.append(link.to_dict() if hasattr(link, "to_dict") else dict(link))
            affiliate_payload["alternative_links"] = alt_links
        except Exception:  # noqa: BLE001 — never break the shopping answer path
            affiliate_payload["error"] = "affiliate_link_generation_failed"
            return response

        processing = dict(response.processing)
        processing["affiliate"] = affiliate_payload
        # ShoppingAssistantResponse is frozen; rebuild via constructor fields.
        return ShoppingAssistantResponse(
            query=response.query,
            intent=response.intent,
            answer=response.answer,
            top_recommendation=response.top_recommendation,
            alternatives=response.alternatives,
            evidence=response.evidence,
            warnings=response.warnings,
            data_status=response.data_status,
            providers_used=response.providers_used,
            fallback_used=response.fallback_used,
            confidence=response.confidence,
            mode=response.mode,
            comparison=response.comparison,
            conversation_id=response.conversation_id,
            disagreements=response.disagreements,
            fallback_reason=response.fallback_reason,
            buy_now_or_wait=response.buy_now_or_wait,
            processing=processing,
            generated_at=response.generated_at,
            personal_recommendation=response.personal_recommendation,
            profile_id=response.profile_id,
        )

    async def add_to_watchlist(
        self,
        *,
        user_id: str | None,
        canonical_product_id: str,
        watchlist_id: str | None = None,
        product_label: str | None = None,
        target_price: float | None = None,
        currency: str = "PHP",
    ) -> dict[str, Any]:
        """Track a product from the assistant conversation. Requires ``user_id``.

        Anonymous callers (``user_id`` falsy) never reach a persistent write —
        this raises before touching the watchlist collaborator.
        """
        if not user_id:
            raise ShoppingAssistantValidationError(
                "Adding items to a watchlist requires an authenticated user_id."
            )
        if self._watchlist_service is None:
            return {
                "added": False,
                "reason": "watchlist_service_unavailable",
                "message": "Watchlists are not available in this deployment.",
            }

        target = self._resolve_or_create_watchlist(watchlist_id, user_id=user_id)
        add_idempotent = getattr(self._watchlist_service, "add_item_idempotent", None)
        if callable(add_idempotent):
            item = await add_idempotent(
                target.watchlist_id,
                canonical_product_id=canonical_product_id,
                product_label=product_label,
                target_price=target_price,
                currency=currency,
            )
        else:
            item = await self._watchlist_service.add_item(
                target.watchlist_id,
                canonical_product_id=canonical_product_id,
                product_label=product_label,
                target_price=target_price,
                currency=currency,
            )
        return {"added": True, "watchlist_id": target.watchlist_id, "item": item.to_dict()}

    def _resolve_or_create_watchlist(self, watchlist_id: str | None, *, user_id: str) -> Any:
        if watchlist_id:
            return self._watchlist_service.get_watchlist(watchlist_id)
        try:
            existing = self._watchlist_service.list_watchlists(owner_id=user_id)
        except TypeError:
            existing = [
                w for w in self._watchlist_service.list_watchlists() if w.owner_id == user_id
            ]
        if existing:
            default = next((w for w in existing if getattr(w, "is_default", False)), None)
            return default or existing[0]
        create = self._watchlist_service.create_watchlist
        try:
            return create(name="My Watchlist", owner_id=user_id, is_default=True)
        except TypeError:
            return create(name="My Watchlist", owner_id=user_id)

    def describe_active_alert_rules(self, user_id: str | None) -> list[dict[str, Any]]:
        """List a user's currently-enabled alert rules. Anonymous users get none."""
        if not user_id or self._alert_rule_service is None:
            return []
        try:
            rules = self._alert_rule_service.list_rules(user_id=user_id, enabled=True)
        except Exception:  # noqa: BLE001
            return []
        return [rule.to_dict() for rule in rules]

    def summarize_recent_alerts(self, user_id: str | None, *, limit: int = 10) -> dict[str, Any]:
        """Summarize a user's recent notifications. Anonymous users get an empty summary."""
        if not user_id or self._notification_center is None:
            return {"count": 0, "notifications": [], "available": False}
        try:
            notifications = self._notification_center.list_notifications(user_id, limit=limit)
        except Exception:  # noqa: BLE001
            return {"count": 0, "notifications": [], "available": False}
        return {
            "count": len(notifications),
            "notifications": [n.to_dict() for n in notifications],
            "available": True,
        }

    def explain_alert_trigger(self, *, user_id: str | None, notification_id: str) -> dict[str, Any]:
        """Explain why a specific notification/alert fired, from its stored metadata."""
        if not user_id or self._notification_center is None:
            return {"explained": False, "reason": "notification_center_unavailable"}
        try:
            notification = self._notification_center.get_notification(
                notification_id, user_id=user_id
            )
        except Exception:  # noqa: BLE001
            return {"explained": False, "reason": "notification_not_found"}
        return {
            "explained": True,
            "title": notification.title,
            "body": notification.body,
            "type": notification.type.value,
            "severity": notification.severity.value,
            "metadata": dict(notification.metadata),
        }

    def recent_price_changes(self, user_id: str | None, *, limit: int = 10) -> list[dict[str, Any]]:
        """Recent price-drop/price-increase notifications for a user."""
        return self._notifications_by_types(
            user_id, {"price_drop", "price_increase", "better_offer"}, limit=limit
        )

    def freshness_warnings(self, user_id: str | None, *, limit: int = 10) -> list[dict[str, Any]]:
        """Recent data-freshness warning notifications for a user."""
        return self._notifications_by_types(user_id, {"freshness_warning"}, limit=limit)

    def _notifications_by_types(
        self, user_id: str | None, types: set[str], *, limit: int
    ) -> list[dict[str, Any]]:
        if not user_id or self._notification_center is None:
            return []
        try:
            notifications = self._notification_center.list_notifications(user_id, limit=200)
        except Exception:  # noqa: BLE001
            return []
        matched = [n for n in notifications if n.type.value in types][:limit]
        return [n.to_dict() for n in matched]

    def recommend_buy_or_wait(self, product_name: str) -> dict[str, Any]:
        """Informational buy-now/wait/keep-watching guidance for one product.

        Read-only and available to anonymous callers — reuses the same
        candidate lookup and evidence pipeline as :meth:`query`, without
        persisting anything.
        """
        intent = self._intent_service.parse(product_name, overrides={"products": [product_name]})
        candidates = self._candidate_service.find_candidates(intent)
        if not candidates:
            return {
                "recommendation": None,
                "message": f"No catalog match found for '{product_name}'.",
            }
        candidate = candidates[0]
        evidence = self._evidence_service.build_for_candidates([candidate])
        guidance = build_buy_now_or_wait(candidate, evidence)
        return {
            "product_id": candidate.product_id,
            "product_name": candidate.product_name,
            "guidance": guidance,
        }

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
            profile_id=request.get("profile_id"),
            user_id=request.get("user_id"),
            decision_id=request.get("decision_id"),
            context_version=request.get("context_version"),
            surface=request.get("surface"),
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
