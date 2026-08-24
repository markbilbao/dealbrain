"""Phase 29.4C: propose research from existing decision evidence only.

Creates a pending confirmation boundary. Does not search, scrape, call
connectors, add products, reprice, or mutate canonical Recommendation / PiqScore.
"""

# ruff: noqa: E501, UP037

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from app.consumer.location import DeliveryContext
from app.consumer.presentation import build_page_view
from app.consumer.session_overlay import apply_session_overlay_to_packet
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_proposal import (
    ResearchProposal,
    ResearchProposalStatus,
    ResearchReason,
)
from app.domain.entities.session_refinement import SessionRecommendationRefinement
from app.domain.entities.shopping_assistant import (
    AssistantConfidence,
    AssistantWarning,
    ConversationOwner,
    ConversationTurn,
    ShoppingAssistantResponse,
    ShoppingQuery,
)
from app.domain.exceptions import (
    ConversationVersionConflictError,
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
    ShoppingAssistantValidationError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.services.answer_from_evidence import (
    _OUTSIDE_HINTS,
    _SOURCE_HINTS,
    _UUID_RE,
    EvidenceAnswerResult,
    _mentions_outside_product,
    compose_evidence_answer,
)
from app.services.decision_evidence_packet import (
    DecisionEvidencePacket,
    packet_from_page_view,
    packet_from_snapshot,
    presentation_fixtures_allowed,
    unavailable_packet,
)
from app.services.refine_session_recommendation import (
    _ATTRIBUTE_ALIASES,
    RefinementResult,
    compose_session_refinement,
    is_refinement_request,
)
from app.services.research_authorization import (
    cancel_research_authorization,
    create_research_authorization_from_proposal,
    current_unconsumed_authorization,
    ignore_client_scope_overrides,
    invalidate_research_authorization,
    upsert_authorization,
)

ProposalLifecycle = Literal[
    "confirm",
    "reconfirm",
    "cancel",
    "ambiguous",
    "replace",
    "propose",
    "stale",
    "no_pending",
]
ProposalAnswerStatus = ResearchProposalStatus | Literal[
    "no_pending_research_proposal",
    "stale_research_proposal",
]
_CONFIRMED_STATUS: ResearchProposalStatus = (
    "research_confirmation_received_but_execution_unavailable"
)
_PERSIST_ATTEMPTS = 3

_FRESHNESS_PHRASES = (
    "today",
    "right now",
    "price now",
    "price today",
    "current price",
    "current prices",
    "still available",
    "still in stock",
    "did the price change",
    "price change",
    "cheaper on amazon today",
    "today's",
    "todays",
    "as of now",
    "live price",
    "latest price",
)
_SOURCE_RESEARCH_PHRASES = (
    "check amazon",
    "check lazada",
    "check shopee",
    "check tiktok",
    "on amazon too",
    "on lazada too",
    "on shopee too",
    "amazon too",
    "lazada too",
    "shopee too",
)
_EXPANSION_PHRASES = (
    "find something cheaper",
    "find something",
    "search for",
    "look for something cheaper",
    "find a cheaper",
    "any cheaper options",
    "newer headphones",
    "any newer",
)
_DESTINATION_PHRASES = (
    "what if i ship",
    "what if we ship",
    "ship this to",
    "ship it to",
    "deliver to",
    "delivery to",
    "shipping to",
)
_CANCEL_PHRASES = (
    "never mind",
    "nevermind",
    "no thanks",
    "no thank you",
    "don't research",
    "do not research",
    "cancel",
    "forget it",
    "no, don't",
    "no dont",
)
_AMBIGUOUS_CONFIRM_PHRASES = (
    "maybe",
    "interesting",
    "what would you check",
    "what would you research",
    "not sure",
    "we'll see",
    "we will see",
    "perhaps",
    "i'll think",
    "hmm",
)
_EXPLICIT_CONFIRM_PHRASES = (
    "yes, research",
    "yes research",
    "yes, check",
    "yes check",
    "go ahead",
    "please do",
    "do it",
    "yes please",
    "yes, please",
    "research it",
    "check it",
    "yes, research that",
    "yes, research those",
    "confirm",
)
_CONFIRM_STANDALONE = re.compile(r"^(yes|yep|yeah|ok|okay|sure|do that|research that)\.?$", re.I)
_CONFIRM_TARGET_RE = re.compile(
    r"(?:yes,?\s+)?(?:research|check|compare)\s+(.+?)(?:\?|$)",
    re.I,
)
_OUTSIDE_NAME_RE = re.compile(
    r"(?:what about|how about|compare|versus|vs\.?|instead(?: of)?|rather get)\s+(.+?)(?:\?|$)",
    re.I,
)
_DESTINATION_NAME_RE = re.compile(
    r"(?:ship(?:ping)?|deliver(?:y)?|send)\s+(?:this |it |them )?(?:to\s+)(.+?)(?:\?|$)",
    re.I,
)
_NON_PRODUCT_TOKENS = frozenset(
    {
        "shipping",
        "price",
        "the price",
        "warranty",
        "this",
        "that",
        "it",
        "them",
        "comfort",
        "battery",
        "anc",
        "today",
        "now",
        "import",
        "the shipping",
        "the warranty",
        "microphone",
        "mic",
        "sources",
        "amazon",
        "lazada",
        "shopee",
    }
)
_TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    **_ATTRIBUTE_ALIASES,
    "warranty": ("warranty", "local warranty", "2-year", "2 year"),
    "availability": ("available", "in stock", "availability"),
}
_TOPIC_QUESTION_HINTS = (
    "which has",
    "which one has",
    "does this include",
    "does it include",
    "does it support",
    "does this support",
    "best microphone",
    "mic quality",
    "warranty",
)


@dataclass(frozen=True, slots=True)
class ResearchNeed:
    reason: ResearchReason
    scope_text: str
    proposal_text: str
    topics: tuple[str, ...] = ()
    outside_names: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    destination_label: str | None = None
    expansion_required: bool = False
    freshness_required: bool = False
    canonical_update_may_be_required: bool = False


@dataclass(frozen=True, slots=True)
class ProposalResult:
    status: ProposalAnswerStatus
    answer: str
    proposal: ResearchProposal | None
    packet: DecisionEvidencePacket
    snapshot: CanonicalDecisionSnapshot | None
    lifecycle: ProposalLifecycle
    authorization: ResearchAuthorization | None = None
    authorization_created: bool = False


class ProposeResearchService:
    """Create or update a pending research proposal. Never executes research."""

    def __init__(
        self,
        snapshots: DecisionSnapshotRepository | None = None,
        conversations: ConversationRepository | None = None,
        *,
        clock=None,  # noqa: ANN001
        id_factory=None,  # noqa: ANN001
    ) -> None:
        self._snapshots = snapshots
        self._conversations = conversations
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def handle(
        self,
        request: ShoppingQuery | dict,
        *,
        location: DeliveryContext | None = None,
        owner: ConversationOwner | None = None,
        snapshot: CanonicalDecisionSnapshot | None = None,
    ) -> ShoppingAssistantResponse | None:
        """Return a proposal response when 29.4C owns the turn; otherwise None."""

        raw = request if isinstance(request, dict) else request.to_dict()
        payload = ignore_client_scope_overrides(dict(raw))
        question = str(payload.get("query") or "").strip()
        if not question:
            raise ShoppingAssistantValidationError("query must not be blank.")
        decision_id = str(payload.get("decision_id") or "").strip()
        if not decision_id:
            return None
        context_version = int(payload.get("context_version") or 1)
        surface = str(payload.get("surface") or "results")
        conversation_id = payload.get("conversation_id")
        client_proposal_id = str(payload.get("proposal_id") or "").strip() or None
        client_proposal_version_raw = payload.get("proposal_version")
        client_proposal_version = (
            int(client_proposal_version_raw) if client_proposal_version_raw else None
        )
        client_confirmation_token = str(payload.get("confirmation_token") or "").strip() or None
        page = surface if surface in {"results", "compare", "why"} else "results"

        packet, resolved = self._resolve_packet(
            decision_id=decision_id,
            context_version=context_version,
            location=location or DeliveryContext(),
            owner=owner,
            conversation_id=str(conversation_id) if conversation_id else None,
            snapshot=snapshot,
            page=page,  # type: ignore[arg-type]
        )
        overlay = self._existing_overlay(
            owner=owner,
            decision_id=packet.decision_id,
            conversation_id=str(conversation_id) if conversation_id else None,
        )
        if overlay is not None:
            packet = apply_session_overlay_to_packet(packet, overlay)
        pending = self._existing_proposal(
            owner=owner,
            decision_id=packet.decision_id,
            conversation_id=str(conversation_id) if conversation_id else None,
        )
        existing_authorizations = self._existing_authorizations(
            owner=owner,
            decision_id=packet.decision_id,
            conversation_id=str(conversation_id) if conversation_id else None,
        )

        before_digest = resolved.content_sha256 if resolved else None
        before_rec = resolved.recommendation.snapshot_sha256 if resolved else None
        before_scores = resolved.canonical_piqscore_set_sha256 if resolved else None
        before_ids = resolved.evaluated_product_ids if resolved else packet.evaluated_product_ids
        before_economics = resolved.offer_economics if resolved else None
        schema_version = resolved.schema_version if resolved else None

        result = compose_research_proposal(
            question,
            packet,
            snapshot=resolved,
            existing=pending,
            overlay=overlay,
            now=self._clock(),
            id_factory=self._id_factory,
            client_proposal_id=client_proposal_id,
            client_proposal_version=client_proposal_version,
        )
        if result is None:
            return None

        if resolved is not None and (
            resolved.content_sha256 != before_digest
            or resolved.recommendation.snapshot_sha256 != before_rec
            or resolved.canonical_piqscore_set_sha256 != before_scores
            or resolved.evaluated_product_ids != before_ids
            or resolved.offer_economics != before_economics
        ):
            raise DecisionSnapshotIntegrityError(decision_id, context_version)

        bound_conversation_id, stored_result = self._persist_proposal(
            result=result,
            owner=owner,
            conversation_id=str(conversation_id) if conversation_id else None,
            snapshot=resolved,
            question=question,
            overlay=overlay,
            existing_authorizations=existing_authorizations,
            client_confirmation_token=client_confirmation_token,
            schema_version=schema_version,
        )
        return self._to_response(
            question,
            stored_result,
            conversation_id=bound_conversation_id or conversation_id,
            overlay=overlay,
        )

    def _resolve_packet(
        self,
        *,
        decision_id: str,
        context_version: int,
        location: DeliveryContext,
        owner: ConversationOwner | None,
        conversation_id: str | None,
        snapshot: CanonicalDecisionSnapshot | None,
        page: str,
    ) -> tuple[DecisionEvidencePacket, CanonicalDecisionSnapshot | None]:
        if snapshot is not None:
            return packet_from_snapshot(snapshot), snapshot

        bound_owner = owner
        if conversation_id and self._conversations is not None:
            context = (
                self._conversations.get_for_owner(conversation_id, owner)
                if owner is not None
                else self._conversations.get(conversation_id)
            )
            if context is None:
                raise ShoppingAssistantNotFoundError(conversation_id)
            if context.owner is None:
                raise DecisionSnapshotOwnershipError(
                    decision_id,
                    "conversation has no owner binding",
                )
            if owner is not None and not context.owner.has_same_identity(owner):
                raise ShoppingAssistantNotFoundError(conversation_id)
            bound_owner = context.owner
            if context.decision_context is not None:
                decision_id = context.decision_context.decision_id
                context_version = context.decision_context.context_version

        if _UUID_RE.match(decision_id):
            if self._snapshots is None:
                raise ShoppingAssistantNotFoundError(decision_id)
            if bound_owner is None:
                raise DecisionSnapshotOwnershipError(
                    decision_id,
                    "snapshot access requires a verified owner",
                )
            loaded = self._snapshots.get_for_owner(decision_id, context_version, bound_owner)
            if loaded is None:
                raise ShoppingAssistantNotFoundError(decision_id)
            return packet_from_snapshot(loaded), loaded

        if not presentation_fixtures_allowed():
            return unavailable_packet(decision_id, context_version), None
        view = build_page_view(
            decision_id=decision_id,
            page=page,  # type: ignore[arg-type]
            location=location,
        )
        return packet_from_page_view(view), None

    def _existing_overlay(
        self,
        *,
        owner: ConversationOwner | None,
        decision_id: str,
        conversation_id: str | None,
    ) -> SessionRecommendationRefinement | None:
        context = self._bound_context(
            owner=owner, decision_id=decision_id, conversation_id=conversation_id
        )
        return context.session_refinement if context is not None else None

    def _existing_proposal(
        self,
        *,
        owner: ConversationOwner | None,
        decision_id: str,
        conversation_id: str | None,
    ) -> ResearchProposal | None:
        context = self._bound_context(
            owner=owner, decision_id=decision_id, conversation_id=conversation_id
        )
        if context is None or context.research_proposal is None:
            return None
        if context.research_proposal.status not in {
            "pending_confirmation",
            _CONFIRMED_STATUS,
        }:
            return None
        return context.research_proposal

    def _existing_authorizations(
        self,
        *,
        owner: ConversationOwner | None,
        decision_id: str,
        conversation_id: str | None,
    ) -> tuple[ResearchAuthorization, ...]:
        context = self._bound_context(
            owner=owner, decision_id=decision_id, conversation_id=conversation_id
        )
        if context is None:
            return ()
        return context.research_authorizations

    def _bound_context(
        self,
        *,
        owner: ConversationOwner | None,
        decision_id: str,
        conversation_id: str | None,
    ) -> Any:
        if self._conversations is None:
            return None
        if conversation_id:
            context = (
                self._conversations.get_for_owner(conversation_id, owner)
                if owner is not None
                else self._conversations.get(conversation_id)
            )
            if context is not None:
                return context
        if owner is not None:
            return self._conversations.find_bound_for_owner(owner, decision_id)
        return None

    def _persist_proposal(
        self,
        *,
        result: ProposalResult,
        owner: ConversationOwner | None,
        conversation_id: str | None,
        snapshot: CanonicalDecisionSnapshot | None,
        question: str,
        overlay: SessionRecommendationRefinement | None,
        existing_authorizations: tuple[ResearchAuthorization, ...] = (),
        client_confirmation_token: str | None = None,
        schema_version: str | None = None,
    ) -> tuple[str | None, ProposalResult]:
        if self._conversations is None or owner is None:
            if result.lifecycle in {"confirm", "reconfirm"}:
                return conversation_id, replace(
                    result,
                    answer=(
                        "I recorded your confirmation, but research cannot be authorized "
                        "without an owner-bound conversation. No research was started."
                    ),
                    authorization=None,
                    authorization_created=False,
                )
            return conversation_id, result

        last_error: Exception | None = None
        working = result
        stored_authorizations = existing_authorizations
        for _attempt in range(_PERSIST_ATTEMPTS):
            try:
                context = None
                if conversation_id:
                    context = self._conversations.get_for_owner(conversation_id, owner)
                if context is None:
                    context = self._conversations.find_bound_for_owner(
                        owner, working.packet.decision_id
                    )
                if context is None:
                    reference = snapshot.to_reference() if snapshot is not None else None
                    if reference is None:
                        if working.lifecycle in {"confirm", "reconfirm"}:
                            return conversation_id, replace(
                                working,
                                answer=(
                                    "I recorded your confirmation, but research cannot be "
                                    "authorized without an owner-bound decision conversation. "
                                    "No research was started."
                                ),
                                authorization=None,
                                authorization_created=False,
                            )
                        return conversation_id, working
                    context = self._conversations.create(owner=owner, decision_context=reference)
                stored_authorizations = context.research_authorizations or stored_authorizations
                proposal = working.proposal
                if proposal is not None:
                    proposal = replace(proposal, conversation_id=context.conversation_id)
                authorization, created = self._authorization_for_persist(
                    working,
                    proposal=proposal,
                    owner=owner,
                    conversation_id=context.conversation_id,
                    existing=stored_authorizations,
                    client_confirmation_token=client_confirmation_token,
                    schema_version=schema_version,
                )
                if authorization is not None:
                    stored_authorizations = upsert_authorization(
                        stored_authorizations, authorization
                    )
                    if proposal is not None and working.lifecycle in {"confirm", "reconfirm"}:
                        proposal = replace(
                            proposal,
                            status=_CONFIRMED_STATUS,
                            confirmation_required=False,
                            authorization_id=authorization.authorization_id,
                            updated_at=self._clock(),
                        )
                stored_proposal = proposal
                if working.status == "cancelled" or working.lifecycle == "cancel":
                    stored_proposal = None
                context = self._conversations.save(
                    replace(
                        context,
                        research_proposal=stored_proposal,
                        research_authorizations=stored_authorizations,
                        session_refinement=overlay or context.session_refinement,
                    ),
                    expected_version=context.persistence_version,
                )
                allowed = (
                    context.decision_context.evaluated_product_ids
                    if context.decision_context is not None
                    else working.packet.evaluated_product_ids
                )
                self._conversations.append_turn(
                    context.conversation_id,
                    ConversationTurn(
                        role="user",
                        intent="general",
                        product_ids=allowed,
                        product_names=(),
                        query=question,
                        created_at=self._clock(),
                        turn_id=self._id_factory(),
                        decision_id=working.packet.decision_id,
                        context_version=working.packet.context_version,
                        action="propose_research",
                    ),
                    last_intent="general",
                    last_product_ids=allowed,
                )
                stored_result = replace(
                    working,
                    proposal=stored_proposal if stored_proposal is not None else proposal,
                    authorization=authorization,
                    authorization_created=created,
                )
                return context.conversation_id, stored_result
            except ConversationVersionConflictError as exc:
                last_error = exc
                conversation_id = conversation_id or getattr(exc, "conversation_id", None)
                continue
        if last_error is not None:
            raise last_error
        return conversation_id, working

    def _authorization_for_persist(
        self,
        result: ProposalResult,
        *,
        proposal: ResearchProposal | None,
        owner: ConversationOwner,
        conversation_id: str,
        existing: tuple[ResearchAuthorization, ...],
        client_confirmation_token: str | None,
        schema_version: str | None,
    ) -> tuple[ResearchAuthorization | None, bool]:
        now = self._clock()
        current = current_unconsumed_authorization(existing)
        if result.lifecycle in {"confirm", "reconfirm"}:
            if proposal is None:
                return None, False
            created_or_reused = create_research_authorization_from_proposal(
                proposal,
                owner=owner,
                conversation_id=conversation_id,
                now=now,
                id_factory=self._id_factory,
                existing=existing,
                client_confirmation_token=client_confirmation_token,
                schema_version=schema_version,
            )
            created = not any(
                item.authorization_id == created_or_reused.authorization_id for item in existing
            )
            return created_or_reused, created
        if result.lifecycle == "cancel" and current is not None:
            return cancel_research_authorization(current, now=now), False
        if result.lifecycle == "replace" and current is not None:
            return invalidate_research_authorization(current, now=now), False
        return None, False

    def _to_response(
        self,
        question: str,
        result: ProposalResult,
        *,
        conversation_id: str | None,
        overlay: SessionRecommendationRefinement | None,
    ) -> ShoppingAssistantResponse:
        packet = result.packet
        proposal = result.proposal
        pending = result.status == "pending_confirmation"
        confirmation_required = pending
        warnings = (
            AssistantWarning(
                message="Research has not started. Explicit confirmation is required first.",
                code="research_not_started",
            ),
        )
        if result.status == "cancelled":
            warnings = (
                AssistantWarning(
                    message="The research proposal was cleared. No research was started.",
                    code="research_not_started",
                ),
            )
        if result.status == _CONFIRMED_STATUS:
            warnings = (
                AssistantWarning(
                    message=(
                        "Research is approved for this request. Execution is not available yet."
                    ),
                    code="research_execution_unavailable",
                ),
            )
        if result.status == "no_pending_research_proposal":
            warnings = (
                AssistantWarning(
                    message="There is no pending research proposal to authorize.",
                    code="research_not_started",
                ),
            )
        if result.status == "stale_research_proposal":
            warnings = (
                AssistantWarning(
                    message=(
                        "That confirmation no longer matches the current research proposal. "
                        "No research was authorized."
                    ),
                    code="research_not_started",
                ),
            )
        processing: dict[str, Any] = {
            "action": "propose_research",
            "answer_status": result.status,
            "response_source": "research_proposal",
            "requires_research_confirmation": confirmation_required,
            "affiliate_influence": False,
            "data_classification": packet.data_classification,
            "decision_id": packet.decision_id,
            "context_version": packet.context_version,
            "canonical_piqscore_snapshot_sha256": packet.canonical_piqscore_set_sha256,
            "canonical_recommendation_snapshot_sha256": packet.recommendation_snapshot_sha256,
            "prompts_included": False,
            "secrets_included": False,
            "execution_started": False,
            "research_executed": False,
            "execution_available": False,
            "authorization_created": result.authorization_created,
        }
        if overlay is not None:
            processing["session_best_piq_product_id"] = overlay.session_best_piq_product_id
            processing["original_best_piq_product_id"] = overlay.original_best_piq_product_id
            processing["session_refinement_version"] = overlay.refinement_version
        elif packet.best_piq_product_id:
            processing["session_best_piq_product_id"] = packet.best_piq_product_id
            processing["original_best_piq_product_id"] = packet.best_piq_product_id
        if proposal is not None:
            processing["research_proposal"] = proposal.to_public_dict()
            processing["research_reason"] = proposal.reason
            processing["proposal_id"] = proposal.proposal_id
            processing["proposal_version"] = proposal.proposal_version
            processing["proposal_status"] = proposal.status
        if result.authorization is not None:
            processing["research_authorization"] = result.authorization.to_public_dict()
            processing["research_authorization_id"] = result.authorization.authorization_id
            processing["authorization_status"] = result.authorization.status
            processing["authorization_version"] = result.authorization.authorization_version
        return ShoppingAssistantResponse(
            query=question,
            intent="general",
            answer=result.answer,
            top_recommendation=None,
            alternatives=(),
            evidence=(),
            warnings=warnings,
            data_status="mock"
            if packet.data_classification == "non_live_contract_fixture"
            else "imported",
            providers_used=("propose_research",),
            fallback_used=True,
            confidence=AssistantConfidence(
                score=0.42 if pending else 0.55,
                band="Medium",
                factors=("research_proposal",),
            ),
            mode="economy",
            conversation_id=conversation_id,
            processing=processing,
            generated_at=self._clock(),
        )


def is_research_request(question: str, packet: DecisionEvidencePacket | None = None) -> bool:
    """True when the shopper asks for evidence/product outside current evidence."""

    text = question.lower()
    if _is_source_inventory_question(text):
        return False
    if extract_outside_product_names(question, packet):
        return True
    if packet is not None and _mentions_outside_product(text, packet):
        return True
    if _has_freshness_intent(text):
        return True
    if _has_source_research_intent(text):
        return True
    if _has_expansion_intent(text):
        return True
    return _has_destination_reeval_intent(text)


def is_explicit_confirmation(question: str, proposal: ResearchProposal | None = None) -> bool:
    text = question.strip().lower()
    if _CONFIRM_STANDALONE.match(text):
        return True
    if any(phrase in text for phrase in _EXPLICIT_CONFIRM_PHRASES):
        return True
    if proposal is not None and text.startswith("yes"):
        names = " ".join(proposal.outside_set_product_names).lower()
        topics = " ".join(proposal.requested_evidence_topics).lower()
        sources = " ".join(proposal.requested_sources).lower()
        referred = any(part and part in text for part in (names, topics, sources) if part)
        if referred or "research" in text or "check" in text:
            return True
    return False


def confirmation_applies_to_proposal(
    question: str,
    proposal: ResearchProposal,
    *,
    client_proposal_id: str | None = None,
    client_proposal_version: int | None = None,
) -> bool:
    """True only when confirmation is generic or clearly refers to this proposal."""

    if client_proposal_id and client_proposal_id != proposal.proposal_id:
        return False
    if client_proposal_version is not None and client_proposal_version != proposal.proposal_version:
        return False
    named_products = {item.lower() for item in extract_outside_product_names(question, None)}
    confirm_target = _confirmation_target_name(question)
    if confirm_target:
        named_products.add(confirm_target)
    proposal_products = {item.lower() for item in proposal.outside_set_product_names}
    product_mentions = {name for name in named_products if _looks_like_product_name(name)}
    if product_mentions and proposal_products and product_mentions.isdisjoint(proposal_products):
        return False
    if product_mentions and not proposal_products:
        return False
    text = question.lower()
    named_sources = tuple(hint for hint in _SOURCE_HINTS if hint in text)
    proposal_sources = tuple(item.lower() for item in proposal.requested_sources)
    if named_sources and proposal_sources and not any(
        source in proposal_sources for source in named_sources
    ):
        return False
    named_destination = _extract_destination(question)
    destination_mismatch = bool(
        named_destination
        and proposal.destination_label
        and named_destination.lower() not in proposal.destination_label.lower()
        and proposal.destination_label.lower() not in named_destination.lower()
    )
    return not destination_mismatch


def _confirmation_target_name(question: str) -> str | None:
    match = _CONFIRM_TARGET_RE.search(question)
    if not match:
        return None
    cleaned = _clean_extracted_name(match.group(1)).lower()
    if not cleaned or cleaned in _NON_PRODUCT_TOKENS:
        return None
    return cleaned


def _looks_like_product_name(name: str) -> bool:
    text = name.strip().lower()
    if not text or text in _NON_PRODUCT_TOKENS:
        return False
    tokens = [token for token in re.split(r"[\s,]+", text) if token]
    if tokens and all(token in set(_SOURCE_HINTS) | {"and", "too", "the"} for token in tokens):
        return False
    price_like = any(token in {"price", "prices", "current", "today"} for token in tokens)
    product_like = any(token in {"airpods", "beats", "sony", "bose"} for token in tokens)
    return not (price_like and not product_like)


def is_cancellation(question: str) -> bool:
    text = question.lower()
    return any(phrase in text for phrase in _CANCEL_PHRASES)


def is_ambiguous_confirmation(question: str) -> bool:
    text = question.strip().lower()
    if is_cancellation(text) or is_explicit_confirmation(text):
        return False
    return any(phrase in text for phrase in _AMBIGUOUS_CONFIRM_PHRASES)


def extract_outside_product_names(
    question: str, packet: DecisionEvidencePacket | None
) -> tuple[str, ...]:
    text = question.lower()
    evaluated = _evaluated_blob(packet)
    found: list[str] = []
    for hint in _OUTSIDE_HINTS:
        if hint in text and hint not in evaluated:
            found.append(_preserve_name(question, hint))
    match = _OUTSIDE_NAME_RE.search(question)
    if match:
        candidate = _clean_extracted_name(match.group(1))
        if (
            candidate
            and candidate.lower() not in _NON_PRODUCT_TOKENS
            and candidate.lower() not in evaluated
            and not _is_evaluated_name(candidate, packet)
        ):
            found.append(candidate)
    return tuple(dict.fromkeys(found))


def compose_research_proposal(
    question: str,
    packet: DecisionEvidencePacket,
    *,
    snapshot: CanonicalDecisionSnapshot | None = None,
    existing: ResearchProposal | None = None,
    overlay: SessionRecommendationRefinement | None = None,
    now: datetime | None = None,
    id_factory=None,  # noqa: ANN001
    client_proposal_id: str | None = None,
    client_proposal_version: int | None = None,
) -> ProposalResult | None:
    """Pure composer. None means 29.4A/29.4B should keep the turn."""

    clock = now or datetime.now(UTC)
    new_id = id_factory or (lambda: str(uuid4()))
    if existing is not None and existing.is_pending:
        if is_cancellation(question):
            cancelled = replace(
                existing,
                status="cancelled",
                confirmation_required=False,
                updated_at=clock,
            )
            return ProposalResult(
                status="cancelled",
                answer=(
                    "Okay — I cleared the pending research proposal. "
                    "No research was started, and the current decision is unchanged."
                ),
                proposal=cancelled,
                packet=packet,
                snapshot=snapshot,
                lifecycle="cancel",
            )
        if is_ambiguous_confirmation(question):
            return ProposalResult(
                status="pending_confirmation",
                answer=(
                    "I still have a pending research proposal, but that reply is not an "
                    f"explicit confirmation. {existing.proposal_text}"
                ),
                proposal=existing,
                packet=packet,
                snapshot=snapshot,
                lifecycle="ambiguous",
            )
        if is_explicit_confirmation(question, existing):
            if not confirmation_applies_to_proposal(
                question,
                existing,
                client_proposal_id=client_proposal_id,
                client_proposal_version=client_proposal_version,
            ):
                return ProposalResult(
                    status="stale_research_proposal",
                    answer=(
                        "That confirmation no longer matches the current research proposal. "
                        "I have not authorized research, and I will not apply an old "
                        "confirmation to a newer request."
                    ),
                    proposal=existing,
                    packet=packet,
                    snapshot=snapshot,
                    lifecycle="stale",
                )
            confirmed = replace(
                existing,
                status=_CONFIRMED_STATUS,
                confirmation_required=False,
                updated_at=clock,
            )
            return ProposalResult(
                status=_CONFIRMED_STATUS,
                answer=(
                    "Research is approved for that exact request. "
                    f"The authorized scope is {existing.scope_text}. "
                    "Execution is not available yet, so no sources were checked, "
                    "no products were added, and the Recommendation is unchanged."
                ),
                proposal=confirmed,
                packet=packet,
                snapshot=snapshot,
                lifecycle="confirm",
            )

    if existing is not None and existing.is_confirmation_recorded:
        if is_cancellation(question):
            cancelled = replace(
                existing,
                status="cancelled",
                confirmation_required=False,
                updated_at=clock,
            )
            return ProposalResult(
                status="cancelled",
                answer=(
                    "Okay — I cancelled the approved research request before execution. "
                    "No research was started, and the current decision is unchanged."
                ),
                proposal=cancelled,
                packet=packet,
                snapshot=snapshot,
                lifecycle="cancel",
            )
        if is_ambiguous_confirmation(question):
            return ProposalResult(
                status=_CONFIRMED_STATUS,
                answer=(
                    "Research is already approved for that exact request. "
                    "Execution is not available yet, and that reply does not change it."
                ),
                proposal=existing,
                packet=packet,
                snapshot=snapshot,
                lifecycle="ambiguous",
            )
        if is_explicit_confirmation(question, existing):
            if not confirmation_applies_to_proposal(
                question,
                existing,
                client_proposal_id=client_proposal_id,
                client_proposal_version=client_proposal_version,
            ):
                return ProposalResult(
                    status="stale_research_proposal",
                    answer=(
                        "That confirmation does not match the approved research request. "
                        "I have not created a new authorization or changed the previous one."
                    ),
                    proposal=existing,
                    packet=packet,
                    snapshot=snapshot,
                    lifecycle="stale",
                )
            return ProposalResult(
                status=_CONFIRMED_STATUS,
                answer=(
                    "Research is already approved for that exact request. "
                    "Execution is not available yet, so no additional research was started."
                ),
                proposal=existing,
                packet=packet,
                snapshot=snapshot,
                lifecycle="reconfirm",
            )

    need = detect_research_need(question, packet, snapshot=snapshot)
    if need is None and existing is not None and existing.is_pending:
        return None
    if need is None:
        if is_explicit_confirmation(question, existing):
            return ProposalResult(
                status="no_pending_research_proposal",
                answer=(
                    "There isn't a pending research proposal to confirm. "
                    "I have not authorized research, and I will not guess what to check."
                ),
                proposal=existing,
                packet=packet,
                snapshot=snapshot,
                lifecycle="no_pending",
            )
        if existing is not None and existing.is_confirmation_recorded:
            return None
        if is_cancellation(question) and existing is None:
            return ProposalResult(
                status="no_pending_research_proposal",
                answer=(
                    "There isn't a pending or approved research request to cancel. "
                    "No research was started."
                ),
                proposal=None,
                packet=packet,
                snapshot=snapshot,
                lifecycle="no_pending",
            )
        return None

    replaced_id = (
        existing.proposal_id
        if existing is not None and (existing.is_pending or existing.is_confirmation_recorded)
        else None
    )
    version = 1 if existing is None else existing.proposal_version + 1
    session_best = (
        overlay.session_best_piq_product_id if overlay is not None else packet.best_piq_product_id
    )
    original = (
        overlay.original_best_piq_product_id if overlay is not None else packet.best_piq_product_id
    )
    proposal = ResearchProposal(
        proposal_id=new_id(),
        decision_id=packet.decision_id,
        proposal_version=version,
        reason=need.reason,
        status="pending_confirmation",
        proposal_text=need.proposal_text,
        scope_text=need.scope_text,
        evaluated_product_ids=packet.evaluated_product_ids,
        requested_evidence_topics=need.topics,
        outside_set_product_names=need.outside_names,
        requested_sources=need.sources,
        destination_label=need.destination_label,
        expansion_required=need.expansion_required,
        freshness_required=need.freshness_required,
        canonical_update_may_be_required=need.canonical_update_may_be_required,
        confirmation_required=True,
        session_best_piq_product_id=session_best,
        original_best_piq_product_id=original,
        canonical_context_version=packet.context_version,
        replaced_proposal_id=replaced_id,
        created_at=clock if existing is None else existing.created_at,
        updated_at=clock,
    )
    return ProposalResult(
        status="pending_confirmation",
        answer=need.proposal_text,
        proposal=proposal,
        packet=packet,
        snapshot=snapshot,
        lifecycle="replace" if replaced_id else "propose",
    )


def detect_research_need(
    question: str,
    packet: DecisionEvidencePacket,
    *,
    snapshot: CanonicalDecisionSnapshot | None = None,
) -> ResearchNeed | None:
    text = question.lower()
    names = ", ".join(packet.names()) if packet.names() else "the products already evaluated"
    outside = extract_outside_product_names(question, packet)
    if not outside and _mentions_outside_product(text, packet):
        hinted = next((hint for hint in _OUTSIDE_HINTS if hint in text), None)
        if hinted:
            outside = (_preserve_name(question, hinted),)

    if outside:
        label = outside[0]
        return ResearchNeed(
            reason="outside_evaluated_set",
            outside_names=outside,
            scope_text=f"{label} and compare it with {names}",
            expansion_required=True,
            canonical_update_may_be_required=True,
            proposal_text=(
                f"{label} wasn't part of the products I evaluated for this decision. "
                f"I can research it and compare it with the current options. "
                "Would you like me to do that?"
            ),
        )

    if _has_expansion_intent(text):
        return ResearchNeed(
            reason="evaluated_set_expansion",
            expansion_required=True,
            canonical_update_may_be_required=True,
            topics=("price",),
            scope_text=f"additional options that may be cheaper than {names}",
            proposal_text=(
                "Finding something cheaper may require looking beyond the products "
                "already evaluated. I can research additional options within your "
                "current constraints and then re-evaluate the decision. "
                "Would you like me to?"
            ),
        )

    if _has_freshness_intent(text):
        source = _requested_sources(text)
        source_note = ""
        if source:
            source_note = (
                f" I can propose checking {source[0].title()} if that source is "
                "available for your market."
            )
        return ResearchNeed(
            reason="freshness_required",
            freshness_required=True,
            sources=source,
            topics=("price", "availability") if "available" in text else ("price",),
            scope_text=f"current offer and pricing evidence for {names}",
            canonical_update_may_be_required=True,
            proposal_text=(
                "I don't have a current check for today's price or availability. "
                f"The captured decision has historical evidence only and is not treated "
                f"as today's price. I can research current offer evidence for {names}."
                f"{source_note} Would you like me to?"
            ),
        )

    if _has_source_research_intent(text) and not _is_source_inventory_question(text):
        sources = _requested_sources(text) or ("that source",)
        label = sources[0].title() if sources[0] != "that source" else "that source"
        return ResearchNeed(
            reason="requested_source",
            sources=() if sources == ("that source",) else sources,
            scope_text=f"{label} offer evidence for {names}, if that source is available",
            proposal_text=(
                f"I can propose checking {label} for this comparison if that source is "
                "available for your market. I have not checked it, and I will not claim "
                "it is already certified. Would you like me to propose that research?"
            ),
        )

    if _has_destination_reeval_intent(text):
        dest = _extract_destination(question)
        current = packet.delivery_label or "the current delivery area"
        if dest and dest.lower() in current.lower():
            return None
        asked = dest or "that destination"
        return ResearchNeed(
            reason="reevaluation_required",
            destination_label=asked,
            canonical_update_may_be_required=True,
            topics=("shipping", "delivered_cost"),
            scope_text=f"delivered cost for {asked} using the current evaluated products",
            proposal_text=(
                f"This decision was evaluated for {current}. Shipping to {asked} can change "
                "delivered cost and might change the Recommendation. I can propose a "
                "destination re-evaluation when that capability is available. "
                "I have not repriced these offers. Would you like me to?"
            ),
        )

    if is_refinement_request(question):
        refinement = compose_session_refinement(question, packet, snapshot=snapshot)
        return _need_from_insufficient_refinement(refinement, names)

    evidence = compose_evidence_answer(question, packet)
    return _need_from_insufficient_evidence(question, evidence, packet, names)


def _need_from_insufficient_refinement(
    refinement: RefinementResult, names: str
) -> ResearchNeed | None:
    if refinement.status == "outside_evaluated_set":
        return None
    if refinement.status == "unsupported_refinement":
        return None
    if refinement.status != "insufficient_evidence":
        return None
    topic = refinement.overlay.priorities.top_priority if refinement.overlay else None
    topic = topic or "that priority"
    return ResearchNeed(
        reason="insufficient_evidence",
        topics=(topic,) if topic != "that priority" else (),
        scope_text=f"{topic} evidence for {names}",
        proposal_text=(
            f"I don't have enough captured {topic} evidence across the products I evaluated "
            "to reliably update the Recommendation. I can research "
            f"{topic} for these options. Would you like me to?"
        ),
    )


def _need_from_insufficient_evidence(
    question: str,
    evidence: EvidenceAnswerResult,
    packet: DecisionEvidencePacket,
    names: str,
) -> ResearchNeed | None:
    text = question.lower()
    topic = _requested_topic(text)
    if evidence.status == "outside_evaluated_set":
        return None
    if evidence.kind == "future_price":
        return None
    if evidence.kind == "sources" and _is_source_inventory_question(text):
        return None
    if evidence.status != "insufficient_evidence" and not (
        topic and not _topic_is_covered(packet, topic) and _looks_like_topic_question(text)
    ):
        return None
    if (
        evidence.status in {"answered", "partially_answered"}
        and evidence.kind not in {"warranty", "freshness"}
        and not (
            topic and not _topic_is_covered(packet, topic) and _looks_like_topic_question(text)
        )
    ):
        return None
    label = topic or _topic_from_kind(evidence.kind)
    if label is None:
        return None
    return ResearchNeed(
        reason="insufficient_evidence",
        topics=(label,),
        scope_text=f"{label} evidence for {names}",
        proposal_text=(
            f"I don't have enough captured {label} evidence to answer that reliably. "
            f"I can research {label} for {names} and then re-evaluate the decision. "
            "Would you like me to?"
        ),
    )


def _topic_from_kind(kind: str) -> str | None:
    return {
        "warranty": "warranty",
        "freshness": "current offer evidence",
        "topic": None,
        "fit": None,
        "product": None,
        "voucher": "voucher",
        "price": None,
        "general": None,
    }.get(kind, kind if kind in {"warranty", "shipping"} else None)


def _looks_like_topic_question(text: str) -> bool:
    return any(hint in text for hint in _TOPIC_QUESTION_HINTS) or bool(_requested_topic(text))


def _requested_topic(text: str) -> str | None:
    for key, aliases in _TOPIC_ALIASES.items():
        if any(alias in text for alias in aliases):
            return key
    return None


def _topic_is_covered(packet: DecisionEvidencePacket, topic: str) -> bool:
    aliases = _TOPIC_ALIASES.get(topic, (topic,))
    for fact in packet.facts:
        blob = f"{fact.topic} {fact.fact}".lower()
        if (
            fact.topic.lower() == topic or any(alias in blob for alias in aliases)
        ) and fact.status != "unknown":
            return True
    return False


def _has_freshness_intent(text: str) -> bool:
    return any(phrase in text for phrase in _FRESHNESS_PHRASES)


def _has_source_research_intent(text: str) -> bool:
    if _is_source_inventory_question(text):
        return False
    if any(phrase in text for phrase in _SOURCE_RESEARCH_PHRASES):
        return True
    return text.startswith("check ") and any(hint in text for hint in _SOURCE_HINTS)


def _is_source_inventory_question(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "did you check",
            "have you checked",
            "what sources",
            "which sources",
            "sources did you",
        )
    )


def _has_expansion_intent(text: str) -> bool:
    return any(phrase in text for phrase in _EXPANSION_PHRASES)


def _has_destination_reeval_intent(text: str) -> bool:
    if "what if" in text and any(token in text for token in ("ship", "deliver", "cebu", "davao")):
        return True
    return any(phrase in text for phrase in _DESTINATION_PHRASES) and (
        "what if" in text or "instead" in text or "cebu" in text or "davao" in text
    )


def _requested_sources(text: str) -> tuple[str, ...]:
    return tuple(hint for hint in _SOURCE_HINTS if hint in text)


def _extract_destination(question: str) -> str | None:
    match = _DESTINATION_NAME_RE.search(question)
    if match:
        return _clean_extracted_name(match.group(1))
    text = question.lower()
    for city in ("cebu", "davao", "manila", "taguig"):
        if city in text:
            return city.title()
    return None


def _evaluated_blob(packet: DecisionEvidencePacket | None) -> str:
    if packet is None:
        return ""
    return " ".join(packet.names()).lower() + " " + " ".join(packet.evaluated_product_ids)


def _is_evaluated_name(name: str, packet: DecisionEvidencePacket | None) -> bool:
    if packet is None:
        return False
    needle = name.lower()
    return any(needle in item.lower() or item.lower() in needle for item in packet.names())


def _clean_extracted_name(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw).strip(" ?!.,")
    cleaned = re.sub(
        r"\b(instead|too|as well|please|for me|this time)\b",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip(" ?!.,")


def _preserve_name(question: str, hint: str) -> str:
    index = question.lower().find(hint)
    if index < 0:
        return hint.title()
    return question[index : index + len(hint)]
