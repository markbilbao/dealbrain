"""Phase 29.4B: refine the session Recommendation from existing decision evidence.

Creates a conversational overlay. Does not research, reprice, add products,
mutate the canonical snapshot, or write account preferences.
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
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.session_refinement import (
    RefinementStatus,
    SessionPriorities,
    SessionQualification,
    SessionRecommendationRefinement,
)
from app.domain.entities.shopping_assistant import (
    AssistantConfidence,
    AssistantWarning,
    ConversationOwner,
    ConversationTurn,
    ShoppingAssistantResponse,
    ShoppingEvidence,
    ShoppingQuery,
)
from app.domain.exceptions import (
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
    ShoppingAssistantValidationError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.services.answer_from_evidence import (
    _OUTSIDE_HINTS,
    _UUID_RE,
    _is_preference_change,
    _mentions_outside_product,
)
from app.services.decision_evidence_packet import (
    DecisionEvidencePacket,
    packet_from_page_view,
    packet_from_snapshot,
    presentation_fixtures_allowed,
    unavailable_packet,
)

_BUDGET_RE = re.compile(
    r"(?:₱|php|p\s*)?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",
    re.I,
)
_ATTRIBUTE_ALIASES: dict[str, tuple[str, ...]] = {
    "comfort": ("comfort", "comfortable", "clamp"),
    "anc": ("anc", "noise cancellation", "noise-cancelling", "noise canceling"),
    "battery": ("battery", "battery life"),
    "microphone": ("microphone", "mic quality", "mic"),
    "price": ("price", "cheaper", "cost", "affordable"),
    "multipoint": ("multipoint", "multi-point", "multi point"),
    "travel": ("travel", "flight", "flights", "long flights"),
    "sound": ("sound quality", "sound", "audio"),
    "warranty": ("warranty", "support"),
    "storage": ("storage",),
}
_RESET_PHRASES = (
    "original priorities",
    "original priority",
    "go back to my original",
    "use my original",
    "reset my priorities",
    "original recommendation",
)
_AMBIGUOUS_PHRASES = (
    "just want the better one",
    "i just want the better",
    "whichever is better",
    "the better one",
)
_EXPANSION_PHRASES = (
    "find something",
    "search for",
    "check amazon",
    "check shopee",
    "check lazada",
    "search reddit",
    "newer headphones",
    "any newer",
    "look up",
    "research",
)
_HARD_PHRASES = ("must ", "required", "i actually need", "i need ", "has to ", "have to ")
_COMPLETE_COST_STATES = frozenset({"final_effective_cost"})
_INCOMPLETE_COST_STATES = frozenset(
    {
        "estimated_landed_cost",
        "price_before_shipping",
        "before_unverified_import_charges",
        "potential_checkout_price",
    }
)
_BOOLEAN_TRUE = frozenset({"true", "yes", "supported", "support"})
_BOOLEAN_FALSE = frozenset({"false", "no", "unsupported", "not supported", "does not support"})
_TRADEOFF_TOPIC_RE = re.compile(
    r"(?:better (?:if|for)|if|for)\s+(?P<topic>[a-z0-9 \-]+?)(?:\s+(?:matters|is|than)|$)",
    re.I,
)


@dataclass(frozen=True, slots=True)
class RefinementResult:
    status: RefinementStatus
    answer: str
    overlay: SessionRecommendationRefinement | None
    packet: DecisionEvidencePacket
    snapshot: CanonicalDecisionSnapshot | None
    applied: bool


def is_refinement_request(question: str) -> bool:
    """True when the shopper is changing session priorities, not asking a fact."""

    text = question.lower()
    if any(phrase in text for phrase in _RESET_PHRASES):
        return True
    if any(phrase in text for phrase in _AMBIGUOUS_PHRASES):
        return True
    if _is_preference_change(text):
        return True
    return any(
        phrase in text
        for phrase in (
            "care more",
            "more important",
            "forget ",
            "price matters",
            "stretch my budget",
            "budget is now",
            "budget is only",
            "my budget is",
            "is required",
            "must support",
            "i actually need",
            "mostly use these",
            "for travel",
            "long flights",
            "which is best for travel",
        )
    ) and not any(
        phrase in text
        for phrase in (
            "why is",
            "why did",
            "what sources",
            "which one has",
            "which one still",
            "does this include",
            "did you check",
            "what was my",
            "what did i",
            "what is this best for",
        )
    )


class RefineSessionRecommendationService:
    """Apply a bounded session Recommendation overlay from captured evidence."""

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

    def refine(
        self,
        request: ShoppingQuery | dict,
        *,
        location: DeliveryContext | None = None,
        owner: ConversationOwner | None = None,
        snapshot: CanonicalDecisionSnapshot | None = None,
    ) -> ShoppingAssistantResponse:
        payload = request if isinstance(request, dict) else request.to_dict()
        question = str(payload.get("query") or "").strip()
        if not question:
            raise ShoppingAssistantValidationError("query must not be blank.")
        decision_id = str(payload.get("decision_id") or "").strip()
        if not decision_id:
            raise ShoppingAssistantValidationError(
                "decision_id is required to refine a session Recommendation."
            )
        context_version = int(payload.get("context_version") or 1)
        surface = str(payload.get("surface") or "results")
        conversation_id = payload.get("conversation_id")
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
        before_digest = resolved.content_sha256 if resolved else None
        before_rec = resolved.recommendation.snapshot_sha256 if resolved else None
        before_scores = resolved.canonical_piqscore_set_sha256 if resolved else None
        before_ids = resolved.evaluated_product_ids if resolved else packet.evaluated_product_ids

        existing = self._existing_overlay(
            owner=owner,
            decision_id=packet.decision_id,
            conversation_id=str(conversation_id) if conversation_id else None,
        )
        result = compose_session_refinement(
            question,
            packet,
            snapshot=resolved,
            existing=existing,
            now=self._clock(),
        )

        if resolved is not None and (
            resolved.content_sha256 != before_digest
            or resolved.recommendation.snapshot_sha256 != before_rec
            or resolved.canonical_piqscore_set_sha256 != before_scores
            or resolved.evaluated_product_ids != before_ids
        ):
            raise DecisionSnapshotIntegrityError(decision_id, context_version)

        bound_conversation_id = self._persist_overlay(
            result=result,
            owner=owner,
            conversation_id=str(conversation_id) if conversation_id else None,
            snapshot=resolved,
            question=question,
        )
        return self._to_response(
            question,
            result,
            conversation_id=bound_conversation_id or conversation_id,
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
            context = self._conversations.get(conversation_id)
            if context is None:
                raise ShoppingAssistantNotFoundError(conversation_id)
            if context.owner is None:
                raise DecisionSnapshotOwnershipError(
                    decision_id,
                    "conversation has no owner binding",
                )
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
        if self._conversations is None:
            return None
        if conversation_id:
            context = (
                self._conversations.get_for_owner(conversation_id, owner)
                if owner is not None
                else self._conversations.get(conversation_id)
            )
            if context is not None and context.session_refinement is not None:
                return context.session_refinement
        if owner is not None:
            context = self._conversations.find_bound_for_owner(owner, decision_id)
            if context is not None:
                return context.session_refinement
        return None

    def _persist_overlay(
        self,
        *,
        result: RefinementResult,
        owner: ConversationOwner | None,
        conversation_id: str | None,
        snapshot: CanonicalDecisionSnapshot | None,
        question: str,
    ) -> str | None:
        if self._conversations is None or owner is None:
            return conversation_id
        context = None
        if conversation_id:
            context = self._conversations.get_for_owner(conversation_id, owner)
        if context is None:
            context = self._conversations.find_bound_for_owner(owner, result.packet.decision_id)
        if context is None:
            reference = snapshot.to_reference() if snapshot is not None else None
            if reference is None:
                return conversation_id
            context = self._conversations.create(owner=owner, decision_context=reference)
        overlay = result.overlay
        if overlay is not None:
            overlay = replace(overlay, conversation_id=context.conversation_id)
            context = self._conversations.save(
                replace(context, session_refinement=overlay),
                expected_version=context.persistence_version,
            )
        elif result.status == "reset_to_original":
            context = self._conversations.save(
                replace(context, session_refinement=None),
                expected_version=context.persistence_version,
            )
        now = self._clock()
        allowed = (
            context.decision_context.evaluated_product_ids
            if context.decision_context is not None
            else result.packet.evaluated_product_ids
        )
        self._conversations.append_turn(
            context.conversation_id,
            ConversationTurn(
                role="user",
                intent="recommendation",
                product_ids=allowed,
                product_names=(),
                query=question,
                created_at=now,
                turn_id=self._id_factory(),
                decision_id=result.packet.decision_id,
                context_version=result.packet.context_version,
                action="refine_session_recommendation",
            ),
            last_intent="recommendation",
            last_product_ids=allowed,
        )
        return context.conversation_id

    def _to_response(
        self,
        question: str,
        result: RefinementResult,
        *,
        conversation_id: str | None,
    ) -> ShoppingAssistantResponse:
        packet = result.packet
        overlay = result.overlay
        evidence_ids = overlay.evidence_ids if overlay else ()
        evidence = tuple(
            ShoppingEvidence(
                evidence_id=item.evidence_id,
                type="recommendation",
                source_id=item.source or "decision-evidence",
                description=item.fact,
                product_id=item.product_id,
            )
            for item in packet.facts
            if item.evidence_id in evidence_ids
        )
        warnings: list[AssistantWarning] = []
        if result.status in {
            "insufficient_evidence",
            "outside_evaluated_set",
            "unsupported_refinement",
        }:
            warnings.append(
                AssistantWarning(
                    message="This answer uses only evidence already captured for the current decision.",
                    code="evidence_bound",
                )
            )
        if result.status == "recommendation_unchanged":
            warnings.append(
                AssistantWarning(
                    message="The session Recommendation remains the current Best Piq for You.",
                    code="recommendation_unchanged",
                )
            )
        band = {
            "recommendation_changed": "High",
            "recommendation_unchanged": "Medium",
            "reset_to_original": "High",
            "insufficient_evidence": "Low",
            "outside_evaluated_set": "Low",
            "unsupported_refinement": "Low",
            "ambiguous_request": "Medium",
            "none_fit_constraint": "Medium",
        }[result.status]
        processing: dict[str, Any] = {
            "action": "refine_session_recommendation",
            "answer_status": result.status,
            "response_source": "session_refinement",
            "requires_research_confirmation": False,
            "affiliate_influence": False,
            "data_classification": packet.data_classification,
            "decision_id": packet.decision_id,
            "context_version": packet.context_version,
            "canonical_piqscore_snapshot_sha256": packet.canonical_piqscore_set_sha256,
            "canonical_recommendation_snapshot_sha256": packet.recommendation_snapshot_sha256,
            "prompts_included": False,
            "secrets_included": False,
            "recommendation_applied": result.applied,
        }
        if overlay is not None:
            processing.update(
                {
                    "session_priorities": overlay.priorities.to_contract(),
                    "recommendation_snapshot_sha256": overlay.recommendation_snapshot_sha256,
                    "session_refinement_version": overlay.refinement_version,
                    "original_best_piq_product_id": overlay.original_best_piq_product_id,
                    "session_best_piq_product_id": overlay.session_best_piq_product_id,
                    "recommendation_changed": overlay.recommendation_changed,
                    "session_qualification_state": overlay.qualification_state,
                    "session_qualification_reasons": (
                        list(overlay.qualification.reasons) if overlay.qualification else []
                    ),
                    "session_material_unknowns": (
                        list(overlay.qualification.material_unknowns)
                        if overlay.qualification
                        else []
                    ),
                    "session_could_change_recommendation": (
                        overlay.qualification.could_change_recommendation
                        if overlay.qualification
                        else False
                    ),
                }
            )
        return ShoppingAssistantResponse(
            query=question,
            intent="recommendation",
            answer=result.answer,
            top_recommendation=None,
            alternatives=(),
            evidence=evidence,
            warnings=tuple(warnings),
            data_status="mock"
            if packet.data_classification == "non_live_contract_fixture"
            else "imported",
            providers_used=("refine_session_recommendation",),
            fallback_used=True,
            confidence=AssistantConfidence(
                score={"High": 0.82, "Medium": 0.55, "Low": 0.28}[band],
                band=band,
                factors=("session_refinement",),
            ),
            mode="economy",
            conversation_id=conversation_id,
            processing=processing,
            generated_at=self._clock(),
        )


def compose_session_refinement(
    question: str,
    packet: DecisionEvidencePacket,
    *,
    snapshot: CanonicalDecisionSnapshot | None = None,
    existing: SessionRecommendationRefinement | None = None,
    now: datetime | None = None,
) -> RefinementResult:
    """Pure overlay composer. Never mutates the snapshot or packet."""

    clock = now or datetime.now(UTC)
    original_id = (
        existing.original_best_piq_product_id
        if existing is not None
        else packet.best_piq_product_id
    )
    if not packet.available:
        return RefinementResult(
            status="insufficient_evidence",
            answer=(
                "Offer details for this decision are not available. "
                "PiqSavi will not invent a session Recommendation from missing evidence."
            ),
            overlay=None,
            packet=packet,
            snapshot=snapshot,
            applied=False,
        )
    if _mentions_outside_product(question.lower(), packet):
        mentioned = next(
            (hint for hint in _OUTSIDE_HINTS if hint in question.lower()),
            "that product",
        )
        names = ", ".join(packet.names()) or "the current evaluated offers"
        return RefinementResult(
            status="outside_evaluated_set",
            answer=(
                f"{mentioned.title()} was not among the offers evaluated for this decision. "
                f"PiqSavi can only reconsider {names} from evidence already captured. "
                "No new product search was started. That remains a later research proposal."
            ),
            overlay=existing,
            packet=packet,
            snapshot=snapshot,
            applied=False,
        )
    if any(phrase in question.lower() for phrase in _EXPANSION_PHRASES):
        return RefinementResult(
            status="unsupported_refinement",
            answer=(
                "That request needs new research or an expanded evaluated set. "
                "PiqSavi did not search, reprice, or add another product. "
                "I can only refine Best Piq for You using the offers already evaluated."
            ),
            overlay=existing,
            packet=packet,
            snapshot=snapshot,
            applied=False,
        )
    if any(phrase in question.lower() for phrase in _AMBIGUOUS_PHRASES):
        return RefinementResult(
            status="ambiguous_request",
            answer=(
                "I can refine Best Piq for You if you tell me which priority changed — "
                "for example comfort, battery life, price, or a required feature. "
                "I will not guess a new Recommendation from a request that does not "
                "materially change your priorities."
            ),
            overlay=existing,
            packet=packet,
            snapshot=snapshot,
            applied=False,
        )

    incoming = interpret_preference_change(question, packet, snapshot=snapshot)
    if incoming.reset_to_original:
        overlay = _build_overlay(
            packet=packet,
            snapshot=snapshot,
            existing=existing,
            priorities=incoming,
            session_best=original_id,
            status="reset_to_original",
            reasons=("You asked to use your original priorities again.",),
            evidence_ids=_recommendation_evidence(packet),
            now=clock,
        )
        name = packet.offer(original_id)
        display = name.display_name if name else "the original Best Piq for You"
        return RefinementResult(
            status="reset_to_original",
            answer=(
                f"I've restored your original session priorities. "
                f"{display} is again the Best Piq for You from the original decision. "
                "PiqScores and the historical Recommendation are unchanged."
            ),
            overlay=overlay,
            packet=packet,
            snapshot=snapshot,
            applied=True,
        )
    if (
        incoming.top_priority is None
        and not incoming.required_features
        and (
            incoming.budget_max is None
            and incoming.use_case is None
            and not incoming.priorities
            and not incoming.deprioritized
        )
    ):
        return RefinementResult(
            status="ambiguous_request",
            answer=(
                "I understand you want to adjust the Recommendation, but I need one "
                "specific priority or constraint that is already present in this decision."
            ),
            overlay=existing,
            packet=packet,
            snapshot=snapshot,
            applied=False,
        )

    merged = existing.priorities.merge(incoming) if existing is not None else incoming
    selection = select_session_best(
        packet,
        merged,
        snapshot=snapshot,
        current_best_id=(
            existing.session_best_piq_product_id if existing is not None else original_id
        ),
        original_id=original_id,
    )
    overlay = None
    if selection.persist:
        overlay = _build_overlay(
            packet=packet,
            snapshot=snapshot,
            existing=existing,
            priorities=merged,
            session_best=selection.product_id,
            status=selection.status,
            reasons=selection.reasons,
            evidence_ids=selection.evidence_ids,
            now=clock,
            qualification=selection.qualification,
        )
    return RefinementResult(
        status=selection.status,
        answer=selection.answer,
        overlay=overlay,
        packet=packet,
        snapshot=snapshot,
        applied=selection.persist,
    )


def interpret_preference_change(
    question: str,
    packet: DecisionEvidencePacket,
    *,
    snapshot: CanonicalDecisionSnapshot | None = None,
) -> SessionPriorities:
    text = question.lower()
    if any(phrase in text for phrase in _RESET_PHRASES):
        return SessionPriorities(reset_to_original=True)
    hard = any(phrase in text for phrase in _HARD_PHRASES)
    keys = _mentioned_attribute_keys(text, packet, snapshot)
    required = tuple(keys) if hard and keys else ()
    preferred = tuple(keys) if not hard and keys else ()
    top = keys[0] if keys else None
    deprioritized: tuple[str, ...] = ()
    if "forget " in text:
        forgotten = _mentioned_attribute_keys(text.split("forget ", 1)[1], packet, snapshot)
        deprioritized = forgotten
        keys = tuple(item for item in keys if item not in forgotten)
        preferred = tuple(item for item in preferred if item not in forgotten)
        top = keys[0] if keys else top
    use_case = None
    if any(token in text for token in ("travel", "flight", "flights")):
        use_case = "travel"
    budget_max = None
    budget_label = None
    if any(token in text for token in ("budget", "₱", "php")):
        match = _BUDGET_RE.search(question.replace(",", ""))
        if match:
            budget_max = float(match.group(1))
            budget_label = f"₱{int(budget_max):,}"
        elif "stretch" in text:
            top = top or "price"
    if "price" in keys or "cheaper" in text or "price matters" in text:
        top = top or "price"
    return SessionPriorities(
        top_priority=top,
        priorities=tuple(dict.fromkeys(keys)),
        required_features=required,
        preferred_features=preferred,
        deprioritized=deprioritized,
        use_case=use_case,
        budget_max=budget_max,
        budget_label=budget_label,
        hard_constraint=hard,
    )


@dataclass(frozen=True, slots=True)
class _Selection:
    product_id: str
    status: RefinementStatus
    answer: str
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    persist: bool
    qualification: SessionQualification | None = None


def select_session_best(
    packet: DecisionEvidencePacket,
    priorities: SessionPriorities,
    *,
    snapshot: CanonicalDecisionSnapshot | None,
    current_best_id: str,
    original_id: str,
) -> _Selection:
    """Pick a session Best Piq from captured evidence only. No scores, no affiliate."""

    names = {item.product_id: item.display_name for item in packet.offers}
    current_name = names.get(current_best_id, "the current Best Piq")
    original_name = names.get(original_id, "the original Best Piq")

    if priorities.budget_max is not None:
        budget = _apply_budget(packet, priorities, current_best_id=current_best_id)
        if budget is not None:
            if budget.product_id != current_best_id and budget.status == "ok":
                return _explain_change(
                    packet,
                    priorities,
                    original_id=original_id,
                    previous_id=current_best_id,
                    chosen_id=budget.product_id,
                    reasons=budget.reasons,
                    evidence_ids=budget.evidence_ids,
                    qualification=_compose_qualification(
                        packet,
                        snapshot,
                        extra_unknowns=budget.material_unknowns,
                        extra_reasons=budget.reasons,
                        could_change=budget.could_change_recommendation,
                    ),
                )
            return _Selection(
                product_id=current_best_id,
                status=budget.status if budget.status != "ok" else "recommendation_unchanged",
                answer=budget.answer,
                reasons=budget.reasons,
                evidence_ids=budget.evidence_ids,
                persist=budget.persist,
                qualification=_compose_qualification(
                    packet,
                    snapshot,
                    extra_unknowns=budget.material_unknowns,
                    extra_reasons=budget.reasons,
                    could_change=budget.could_change_recommendation,
                    force_qualified=budget.status
                    in {"none_fit_constraint", "insufficient_evidence"},
                ),
            )

    if priorities.required_features:
        hard = _apply_required_features(
            packet,
            snapshot,
            priorities.required_features,
            current_best_id=current_best_id,
        )
        if hard.status != "ok":
            return _Selection(
                product_id=current_best_id,
                status=hard.status,
                answer=hard.answer,
                reasons=hard.reasons,
                evidence_ids=hard.evidence_ids,
                persist=hard.persist,
                qualification=_compose_qualification(
                    packet,
                    snapshot,
                    extra_unknowns=hard.material_unknowns,
                    extra_reasons=hard.reasons,
                    could_change=hard.could_change_recommendation,
                    force_qualified=True,
                ),
            )
        if hard.product_id and hard.product_id != current_best_id:
            return _explain_change(
                packet,
                priorities,
                original_id=original_id,
                previous_id=current_best_id,
                chosen_id=hard.product_id,
                reasons=hard.reasons,
                evidence_ids=hard.evidence_ids,
                qualification=_compose_qualification(
                    packet,
                    snapshot,
                    extra_unknowns=hard.material_unknowns,
                    extra_reasons=hard.reasons,
                    could_change=hard.could_change_recommendation,
                ),
            )
        if hard.product_id == current_best_id:
            return _Selection(
                product_id=current_best_id,
                status="recommendation_unchanged",
                answer=hard.answer
                or f"{current_name} already satisfies the required feature from captured evidence.",
                reasons=hard.reasons,
                evidence_ids=hard.evidence_ids,
                persist=True,
                qualification=_compose_qualification(
                    packet,
                    snapshot,
                    extra_unknowns=hard.material_unknowns,
                    extra_reasons=hard.reasons,
                    could_change=hard.could_change_recommendation,
                ),
            )

    topics = _priority_topics(priorities)
    last_comparison: _CompareResult | None = None
    for index, topic in enumerate(topics):
        comparison = _compare_attribute(packet, snapshot, topic)
        last_comparison = comparison
        if comparison.insufficient:
            if index == 0:
                return _Selection(
                    product_id=current_best_id,
                    status="insufficient_evidence",
                    answer=(
                        f"I understand {topic} matters more now, but I don't have enough captured "
                        f"{topic} evidence across the evaluated options to reliably change the "
                        f"Recommendation. {current_name} remains Best Piq for You. "
                        "No additional research was started."
                    ),
                    reasons=(f"Insufficient captured {topic} evidence.",),
                    evidence_ids=comparison.evidence_ids,
                    persist=True,
                    qualification=_compose_qualification(
                        packet,
                        snapshot,
                        extra_unknowns=comparison.material_unknowns
                        or (f"No captured {topic} evidence across the evaluated set.",),
                        extra_reasons=(f"Insufficient captured {topic} evidence.",),
                        could_change=False,
                        force_qualified=True,
                    ),
                )
            continue
        if comparison.winner_id and comparison.winner_id != current_best_id:
            return _explain_change(
                packet,
                priorities,
                original_id=original_id,
                previous_id=current_best_id,
                chosen_id=comparison.winner_id,
                reasons=comparison.reasons,
                evidence_ids=comparison.evidence_ids,
                qualification=_compose_qualification(
                    packet,
                    snapshot,
                    extra_unknowns=comparison.material_unknowns,
                    extra_reasons=comparison.reasons[:1],
                    could_change=comparison.could_change_recommendation,
                ),
            )
        if comparison.winner_id is None and index < len(topics) - 1:
            continue
        return _Selection(
            product_id=current_best_id,
            status="recommendation_unchanged",
            answer=(
                f"I recorded that {topic} matters more now. {current_name} still best satisfies "
                f"that updated priority from the captured evidence. "
                f"{original_name} remains the historical Recommendation. PiqScores are unchanged."
            ),
            reasons=comparison.reasons
            or (f"{current_name} still best matches the updated {topic} priority.",),
            evidence_ids=comparison.evidence_ids or _recommendation_evidence(packet),
            persist=True,
            qualification=_compose_qualification(
                packet,
                snapshot,
                extra_unknowns=comparison.material_unknowns,
                could_change=comparison.could_change_recommendation,
            ),
        )

    return _Selection(
        product_id=current_best_id,
        status="recommendation_unchanged",
        answer=(
            f"I recorded your clarification. {current_name} remains Best Piq for You. "
            "The captured evidence does not justify switching."
        ),
        reasons=("No differentiating captured evidence for a switch.",),
        evidence_ids=_recommendation_evidence(packet),
        persist=True,
        qualification=_compose_qualification(
            packet,
            snapshot,
            extra_unknowns=last_comparison.material_unknowns if last_comparison else (),
            could_change=bool(last_comparison and last_comparison.could_change_recommendation),
        ),
    )


def _explain_change(
    packet: DecisionEvidencePacket,
    priorities: SessionPriorities,
    *,
    original_id: str,
    previous_id: str,  # noqa: ARG001 — retained for call-site symmetry
    chosen_id: str,
    reasons: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    qualification: SessionQualification | None,
) -> _Selection:
    names = {item.product_id: item.display_name for item in packet.offers}
    scores = {item.product_id: item.piqscore for item in packet.offers}
    chosen = names.get(chosen_id, chosen_id)
    original = names.get(original_id, original_id)
    priority = priorities.top_priority or priorities.use_case or "your updated priority"
    original_score = scores.get(original_id)
    chosen_score = scores.get(chosen_id)
    score_note = ""
    if original_score is not None and chosen_score is not None and original_score != chosen_score:
        higher = original if (original_score or 0) > (chosen_score or 0) else chosen
        score_note = (
            f" {higher} still has the higher objective PiqScore, but PiqScore evaluates "
            "the offer and Best Piq for You reflects what best fits the priorities you just clarified."
        )
    why = reasons[0] if reasons else f"Captured evidence for {priority} favors {chosen}."
    return _Selection(
        product_id=chosen_id,
        status="recommendation_changed",
        answer=(
            f"Originally I recommended {original}. After you said {priority} matters more, "
            f"{chosen} is now my Best Piq for You for this session. {why}{score_note} "
            "The historical decision and all PiqScores are unchanged."
        ),
        reasons=reasons or (why,),
        evidence_ids=evidence_ids,
        persist=True,
        qualification=qualification,
    )


def _build_overlay(
    *,
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    existing: SessionRecommendationRefinement | None,
    priorities: SessionPriorities,
    session_best: str,
    status: RefinementStatus,
    reasons: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    now: datetime,
    qualification: SessionQualification | None = None,
) -> SessionRecommendationRefinement:
    original = (
        existing.original_best_piq_product_id
        if existing is not None
        else packet.best_piq_product_id
    )
    version = 1 if existing is None else existing.refinement_version + 1
    created = existing.created_at if existing is not None else now
    return SessionRecommendationRefinement(
        decision_id=packet.decision_id,
        canonical_context_version=packet.context_version,
        refinement_version=version,
        original_best_piq_product_id=original,
        session_best_piq_product_id=session_best,
        priorities=priorities,
        recommendation_changed=session_best != original,
        status=status,
        evidence_ids=evidence_ids,
        reasons=reasons,
        qualification=qualification or _compose_qualification(packet, snapshot),
        created_at=created,
        updated_at=now,
    )


def _mentioned_attribute_keys(
    text: str,
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
) -> list[str]:
    found: list[str] = []
    catalog = _attribute_catalog(packet, snapshot)
    for key, aliases in catalog.items():
        if any(alias in text for alias in aliases):
            found.append(key)
    return found


def _attribute_catalog(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
) -> dict[str, tuple[str, ...]]:
    catalog = dict(_ATTRIBUTE_ALIASES)
    if snapshot is not None:
        for product in snapshot.product_presentation:
            for attr in product.fit_attributes:
                key = attr.key.lower()
                catalog.setdefault(key, (key, attr.label.lower()))
        if snapshot.shopper_context is not None:
            if snapshot.shopper_context.top_priority:
                label = snapshot.shopper_context.top_priority.lower()
                catalog.setdefault(label, (label,))
            for item in snapshot.shopper_context.priorities:
                catalog.setdefault(item.lower(), (item.lower(),))
    for fact in packet.facts:
        topic = fact.topic.lower()
        if topic not in {"price", "shipping", "import", "tax", "source", "unknown", "freshness"}:
            catalog.setdefault(topic, (topic,))
    return catalog


def _priority_topics(priorities: SessionPriorities) -> tuple[str, ...]:
    ordered = (
        *((priorities.top_priority,) if priorities.top_priority else ()),
        *priorities.priorities,
        *priorities.preferred_features,
        *((priorities.use_case,) if priorities.use_case else ()),
    )
    skipped = set(priorities.deprioritized)
    return tuple(item for item in dict.fromkeys(ordered) if item and item not in skipped)


def _complete_cost(offer: Any) -> float | None:
    if offer.price_amount is None:
        return None
    if offer.price_state not in _COMPLETE_COST_STATES:
        return None
    if offer.import_status in {"unknown", "unverified", "estimated"}:
        return None
    return offer.price_amount


def _cost_unknown_reason(offer: Any) -> str | None:
    name = offer.display_name
    if offer.price_amount is None:
        return f"{name} has no captured total cost."
    if offer.price_state in _INCOMPLETE_COST_STATES:
        return f"{name} is captured as {offer.price_label or offer.price_state}, not a complete buying cost."
    if offer.import_status in {"unknown", "unverified", "estimated"}:
        return f"{name} has material import uncertainty ({offer.import_status})."
    return None


@dataclass(frozen=True, slots=True)
class _ConstraintResult:
    status: RefinementStatus | Literal["ok"]
    product_id: str
    answer: str
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    persist: bool
    material_unknowns: tuple[str, ...] = ()
    could_change_recommendation: bool = False


def _apply_budget(
    packet: DecisionEvidencePacket,
    priorities: SessionPriorities,
    *,
    current_best_id: str,
) -> _ConstraintResult | None:
    if priorities.budget_max is None:
        return None
    budget = priorities.budget_max
    label = priorities.budget_label or "the new amount"
    affordable: list[str] = []
    unknown: list[str] = []
    over: list[str] = []
    unknown_reasons: list[str] = []
    names = {item.product_id: item.display_name for item in packet.offers}
    for offer in packet.offers:
        cost = _complete_cost(offer)
        if cost is None:
            unknown.append(offer.product_id)
            reason = _cost_unknown_reason(offer)
            if reason:
                unknown_reasons.append(reason)
            continue
        if cost <= budget:
            affordable.append(offer.product_id)
        else:
            over.append(offer.product_id)
    current_name = names.get(current_best_id, "the current Best Piq")
    if not affordable:
        detail = "No evaluated offer has a captured complete cost that fits that session budget."
        if unknown:
            detail += " Unknown, estimated, before-shipping, or import-uncertain cost is not treated as affordable."
        if over:
            detail += (
                f" {len(over)} evaluated offer(s) have a known complete cost above the budget."
            )
        return _ConstraintResult(
            status="none_fit_constraint",
            product_id=current_best_id,
            answer=(
                f"I applied your session budget of {label}. {detail} "
                "I did not search for other products or reprice these offers. "
                f"{current_name} remains the current session Best Piq."
            ),
            reasons=(detail, *unknown_reasons[:2]),
            evidence_ids=_price_evidence(packet),
            persist=True,
            material_unknowns=tuple(unknown_reasons),
            could_change_recommendation=bool(unknown),
        )
    if current_best_id in affordable:
        extra = ""
        if unknown:
            extra = (
                " Offers with incomplete or unknown cost were not treated as fitting the budget."
            )
        return _ConstraintResult(
            status="ok",
            product_id=current_best_id,
            answer=(
                f"I applied your session budget of {label}. {current_name} already has a captured "
                f"final effective cost within that budget.{extra}"
            ),
            reasons=(f"{current_name} fits the session budget from captured complete cost.",),
            evidence_ids=_price_evidence(packet),
            persist=True,
            material_unknowns=tuple(unknown_reasons),
            could_change_recommendation=bool(unknown),
        )
    if len(affordable) == 1:
        chosen = affordable[0]
        return _ConstraintResult(
            status="ok",
            product_id=chosen,
            answer="",
            reasons=(
                f"{names.get(chosen, chosen)} is the only evaluated offer with a captured "
                f"final effective cost within {label}.",
            ),
            evidence_ids=_price_evidence(packet),
            persist=True,
            material_unknowns=tuple(unknown_reasons),
            could_change_recommendation=bool(unknown),
        )
    return _ConstraintResult(
        status="insufficient_evidence",
        product_id=current_best_id,
        answer=(
            f"I applied your session budget of {label}. {current_name} exceeds that budget, "
            f"and {len(affordable)} evaluated offers have captured complete costs that fit. "
            "Those offers are not further distinguished by captured evidence, so I will not "
            "invent a session Best Piq among them."
        ),
        reasons=("Multiple evaluated offers fit the session budget without further distinction.",),
        evidence_ids=_price_evidence(packet),
        persist=True,
        material_unknowns=tuple(unknown_reasons),
        could_change_recommendation=True,
    )


@dataclass(frozen=True, slots=True)
class _HardResult:
    status: RefinementStatus | Literal["ok"]
    product_id: str | None
    answer: str
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    persist: bool
    material_unknowns: tuple[str, ...] = ()
    could_change_recommendation: bool = False


def _apply_required_features(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    features: tuple[str, ...],
    *,
    current_best_id: str,
) -> _HardResult:
    names = {item.product_id: item.display_name for item in packet.offers}
    for feature in features:
        statuses = {
            offer.product_id: _feature_status(packet, snapshot, offer.product_id, feature)
            for offer in packet.offers
        }
        known_true = [pid for pid, status in statuses.items() if status == "true"]
        known_false = [pid for pid, status in statuses.items() if status == "false"]
        unknown = [pid for pid, status in statuses.items() if status == "unknown"]
        evidence_ids = _attribute_evidence(packet, snapshot, feature)
        unknown_note = (
            f"{len(unknown)} evaluated option(s) have unknown {feature} evidence. "
            "Unknown is not treated as false and is not treated as confirmed true."
        )
        if not known_true:
            if known_false and not unknown:
                return _HardResult(
                    status="none_fit_constraint",
                    product_id=current_best_id,
                    answer=(
                        f"I understand {feature} is required, but every evaluated option has "
                        f"captured evidence that it does not support {feature}. "
                        "I did not invent a session Best Piq that violates that requirement."
                    ),
                    reasons=(f"No evaluated option has captured {feature} support.",),
                    evidence_ids=evidence_ids,
                    persist=True,
                )
            return _HardResult(
                status="insufficient_evidence",
                product_id=current_best_id,
                answer=(
                    f"I understand {feature} is required, but I don't have captured evidence "
                    f"that any evaluated option supports it. Unknown is not treated as false, "
                    "and I will not invent that support. No research was started."
                ),
                reasons=(f"No captured true evidence for required {feature}.",),
                evidence_ids=evidence_ids,
                persist=True,
                material_unknowns=(unknown_note,) if unknown else (),
                could_change_recommendation=bool(unknown),
            )
        if current_best_id in known_true:
            return _HardResult(
                status="ok",
                product_id=current_best_id,
                answer=(
                    f"{names.get(current_best_id, current_best_id)} already has captured "
                    f"evidence of {feature} support." + (f" {unknown_note}" if unknown else "")
                ),
                reasons=(
                    f"{names.get(current_best_id, current_best_id)} has captured {feature} support.",
                    *(() if not unknown else (unknown_note,)),
                ),
                evidence_ids=evidence_ids,
                persist=True,
                material_unknowns=(unknown_note,) if unknown else (),
                could_change_recommendation=False,
            )
        if len(known_true) == 1:
            chosen = known_true[0]
            return _HardResult(
                status="ok",
                product_id=chosen,
                answer="",
                reasons=(
                    f"{names.get(chosen, chosen)} has captured evidence of {feature} support.",
                    *(() if not unknown else (unknown_note,)),
                ),
                evidence_ids=evidence_ids,
                persist=True,
                material_unknowns=(unknown_note,) if unknown else (),
                could_change_recommendation=bool(unknown),
            )
        return _HardResult(
            status="insufficient_evidence",
            product_id=current_best_id,
            answer=(
                f"I understand {feature} is required. {len(known_true)} evaluated options have "
                f"captured support, and captured evidence does not distinguish them further. "
                "I will not invent a session Best Piq among those confirmed options."
            ),
            reasons=(
                f"Multiple options have captured {feature} support without further distinction.",
            ),
            evidence_ids=evidence_ids,
            persist=True,
            material_unknowns=(unknown_note,) if unknown else (),
            could_change_recommendation=True,
        )
    return _HardResult(
        status="ok",
        product_id=None,
        answer="",
        reasons=(),
        evidence_ids=(),
        persist=False,
    )


@dataclass(frozen=True, slots=True)
class _CompareResult:
    winner_id: str | None
    insufficient: bool
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    material_unknowns: tuple[str, ...] = ()
    could_change_recommendation: bool = False


def _compare_attribute(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    topic: str,
) -> _CompareResult:
    if topic == "price":
        return _compare_complete_cost(packet)

    aliases = _attribute_catalog(packet, snapshot).get(topic, (topic,))
    names = {item.product_id: item.display_name for item in packet.offers}
    evidence_ids: list[str] = []
    tradeoff_ids: list[str] = []
    reason_ids: list[str] = []
    known_ids: list[str] = []
    boolean_true: list[str] = []
    boolean_false: list[str] = []
    unknown_ids: list[str] = []
    known_facts: dict[str, str] = {}

    if snapshot is not None:
        for item in snapshot.alternative_tradeoffs:
            if _reason_prefers_topic(item.reason, topic, aliases):
                evidence_ids.extend(item.evidence_ids)
                tradeoff_ids.append(item.product_id)
                known_facts.setdefault(item.product_id, item.reason)
        for item in snapshot.recommendation_reasons:
            related = (item.related_attribute or item.shopper_priority or "").lower()
            if item.product_id and (
                related == topic or _reason_prefers_topic(item.reason, topic, aliases)
            ):
                evidence_ids.extend(item.evidence_ids)
                reason_ids.append(item.product_id)
                known_facts.setdefault(item.product_id, item.reason)
        for item in snapshot.best_for:
            if any(alias in item.label.lower() for alias in aliases) or topic in item.label.lower():
                evidence_ids.extend(item.evidence_ids)
        for product in snapshot.product_presentation:
            for attr in product.fit_attributes:
                if attr.key.lower() != topic and attr.label.lower() not in aliases:
                    continue
                evidence_ids.extend(attr.evidence_ids)
                if attr.status == "unknown":
                    unknown_ids.append(product.product_id)
                    continue
                status = _boolean_from_text(attr.value)
                if status == "true":
                    boolean_true.append(product.product_id)
                    known_ids.append(product.product_id)
                    known_facts.setdefault(product.product_id, attr.display_value())
                elif status == "false":
                    boolean_false.append(product.product_id)
                    known_ids.append(product.product_id)
                    known_facts.setdefault(product.product_id, attr.display_value())
                else:
                    known_ids.append(product.product_id)
                    known_facts.setdefault(product.product_id, attr.display_value())
        for item in snapshot.evidence:
            if item.topic.lower() != topic and not _reason_prefers_topic(item.fact, topic, aliases):
                continue
            evidence_ids.append(item.evidence_id)
            known_ids.append(item.product_id)
            known_facts.setdefault(item.product_id, item.fact)
    else:
        for fact in packet.facts:
            blob = f"{fact.topic} {fact.fact}".lower()
            if fact.topic.lower() != topic and not any(alias in blob for alias in aliases):
                continue
            evidence_ids.append(fact.evidence_id)
            if fact.product_id:
                if fact.status == "unknown":
                    unknown_ids.append(fact.product_id)
                    continue
                known_ids.append(fact.product_id)
                known_facts.setdefault(fact.product_id, fact.fact)
        for offer in packet.offers:
            if offer.alternative_reason and _reason_prefers_topic(
                offer.alternative_reason, topic, aliases
            ):
                tradeoff_ids.append(offer.product_id)
                known_facts.setdefault(offer.product_id, offer.alternative_reason)

    tradeoff_ids = list(dict.fromkeys(tradeoff_ids))
    reason_ids = list(dict.fromkeys(reason_ids))
    known_ids = list(dict.fromkeys(known_ids))
    boolean_true = list(dict.fromkeys(boolean_true))
    boolean_false = list(dict.fromkeys(boolean_false))
    missing = [
        offer.product_id
        for offer in packet.offers
        if offer.product_id not in known_ids
        and offer.product_id not in tradeoff_ids
        and offer.product_id not in reason_ids
        and offer.product_id not in boolean_true
        and offer.product_id not in boolean_false
    ]
    unknown_ids = list(dict.fromkeys([*unknown_ids, *missing]))
    unknown_note = (
        tuple(
            f"{names.get(pid, pid)} has no captured comparable {topic} evidence."
            for pid in unknown_ids
        )
        if unknown_ids
        else ()
    )

    if tradeoff_ids:
        unique = list(dict.fromkeys(tradeoff_ids))
        if len(unique) == 1:
            chosen = unique[0]
            return _CompareResult(
                winner_id=chosen,
                insufficient=False,
                reasons=(
                    known_facts.get(chosen)
                    or f"Captured trade-off evidence prefers {names.get(chosen, chosen)} when {topic} matters more.",
                ),
                evidence_ids=tuple(dict.fromkeys(evidence_ids)),
                material_unknowns=unknown_note,
                could_change_recommendation=bool(unknown_ids),
            )
        return _CompareResult(
            winner_id=None,
            insufficient=False,
            reasons=(f"Captured {topic} trade-offs do not distinguish a single option.",),
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
            material_unknowns=unknown_note,
        )

    if reason_ids:
        unique = list(dict.fromkeys(reason_ids))
        if len(unique) == 1:
            chosen = unique[0]
            return _CompareResult(
                winner_id=chosen,
                insufficient=False,
                reasons=(
                    known_facts.get(chosen)
                    or f"Captured Recommendation reasoning selected {names.get(chosen, chosen)} for {topic}.",
                ),
                evidence_ids=tuple(dict.fromkeys(evidence_ids)),
                material_unknowns=unknown_note,
                could_change_recommendation=bool(unknown_ids),
            )

    if boolean_true or boolean_false:
        if len(boolean_true) == 1 and not (set(known_ids) - set(boolean_true) - set(boolean_false)):
            chosen = boolean_true[0]
            return _CompareResult(
                winner_id=chosen,
                insufficient=False,
                reasons=(f"{names.get(chosen, chosen)} has captured {topic} support.",),
                evidence_ids=tuple(dict.fromkeys(evidence_ids)),
                material_unknowns=unknown_note,
                could_change_recommendation=bool(unknown_ids),
            )
        if boolean_true and not unknown_ids and len(set(boolean_true)) > 1:
            return _CompareResult(
                winner_id=None,
                insufficient=False,
                reasons=(f"Captured {topic} support does not distinguish the evaluated options.",),
                evidence_ids=tuple(dict.fromkeys(evidence_ids)),
            )

    if not known_ids and not reason_ids and not tradeoff_ids:
        return _CompareResult(
            winner_id=None,
            insufficient=True,
            reasons=(f"No captured {topic} evidence exists in this decision.",),
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
            material_unknowns=unknown_note or (f"No captured {topic} evidence.",),
        )

    unique_known = list(dict.fromkeys(known_ids))
    if len(unique_known) == 1:
        chosen = unique_known[0]
        return _CompareResult(
            winner_id=chosen,
            insufficient=False,
            reasons=(
                known_facts.get(chosen)
                or f"{names.get(chosen, chosen)} is the only evaluated option with captured {topic} evidence.",
            ),
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
            material_unknowns=unknown_note,
            could_change_recommendation=True,
        )

    return _CompareResult(
        winner_id=None,
        insufficient=True,
        reasons=(
            f"Captured {topic} values are not comparable under an approved contract, "
            "so I will not invent an ordering."
        ),
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        material_unknowns=unknown_note,
    )


def _compare_complete_cost(packet: DecisionEvidencePacket) -> _CompareResult:
    priced: list[tuple[float, str, str]] = []
    unknown_notes: list[str] = []
    for offer in packet.offers:
        cost = _complete_cost(offer)
        if cost is None:
            reason = _cost_unknown_reason(offer)
            if reason:
                unknown_notes.append(reason)
            continue
        priced.append((cost, offer.product_id, offer.display_name))
    if not priced:
        return _CompareResult(
            winner_id=None,
            insufficient=True,
            reasons=("No captured final effective cost is available to compare price.",),
            evidence_ids=_price_evidence(packet),
            material_unknowns=tuple(unknown_notes),
            could_change_recommendation=bool(unknown_notes),
        )
    priced.sort()
    lowest = priced[0][0]
    winners = [item for item in priced if item[0] == lowest]
    if len(winners) != 1:
        return _CompareResult(
            winner_id=None,
            insufficient=False,
            reasons=("Captured complete costs do not distinguish a single lowest-price offer.",),
            evidence_ids=_price_evidence(packet),
            material_unknowns=tuple(unknown_notes),
        )
    _, winner_id, winner_name = winners[0]
    return _CompareResult(
        winner_id=winner_id,
        insufficient=False,
        reasons=(
            f"{winner_name} has the lowest captured final effective cost "
            "among evaluated offers with complete known cost.",
        ),
        evidence_ids=_price_evidence(packet),
        material_unknowns=tuple(unknown_notes),
        could_change_recommendation=bool(unknown_notes),
    )


def _reason_prefers_topic(reason: str, topic: str, aliases: tuple[str, ...]) -> bool:
    text = reason.lower()
    for alias in (topic, *aliases):
        if re.search(
            rf"(?:better (?:if|for)|if|for)\s+{re.escape(alias)}\b",
            text,
        ):
            return True
        if re.search(
            rf"\b{re.escape(alias)}\s+(?:matters more|is more important|is required|is now)",
            text,
        ):
            return True
    return False


def _boolean_from_text(value: str) -> Literal["true", "false", "unknown"]:
    text = value.strip().lower()
    if text in {"unknown", ""}:
        return "unknown"
    if text in _BOOLEAN_FALSE or text.startswith("not supported") or text.startswith("unsupported"):
        return "false"
    if text in _BOOLEAN_TRUE:
        return "true"
    return "unknown"


def _feature_status(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    product_id: str,
    feature: str,
) -> Literal["true", "false", "unknown"]:
    aliases = _attribute_catalog(packet, snapshot).get(feature, (feature,))
    if snapshot is not None:
        presentation = next(
            (item for item in snapshot.product_presentation if item.product_id == product_id),
            None,
        )
        if presentation is not None:
            for attr in presentation.fit_attributes:
                if attr.key.lower() != feature and attr.label.lower() not in aliases:
                    continue
                if attr.status == "unknown":
                    return "unknown"
                return _boolean_from_text(attr.value)
        for item in snapshot.evidence:
            if item.product_id != product_id:
                continue
            if item.topic.lower() == feature:
                return _boolean_from_text(item.fact)
    for fact in packet.facts:
        if fact.product_id != product_id:
            continue
        if fact.topic.lower() == feature:
            if fact.status == "unknown":
                return "unknown"
            return _boolean_from_text(fact.fact)
    return "unknown"


def _compose_qualification(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    *,
    extra_unknowns: tuple[str, ...] = (),
    extra_reasons: tuple[str, ...] = (),
    could_change: bool = False,
    force_qualified: bool = False,
) -> SessionQualification:
    reasons: list[str] = []
    unknowns: list[str] = []
    reverse = could_change
    if snapshot is not None and snapshot.qualification is not None:
        canonical = snapshot.qualification
        unknowns.extend(canonical.material_unknowns)
        if canonical.is_qualified:
            reasons.extend(canonical.reasons)
            reverse = reverse or canonical.could_change_recommendation
    elif packet.is_qualified:
        if packet.qualified_reason:
            reasons.append(packet.qualified_reason)
        unknowns.extend(packet.unknowns)
        reverse = True
    unknowns.extend(extra_unknowns)
    reasons.extend(extra_reasons)
    reasons = list(dict.fromkeys(item for item in reasons if item and item.strip()))
    unknowns = list(dict.fromkeys(item for item in unknowns if item and item.strip()))
    qualified = (
        force_qualified
        or reverse
        or bool(unknowns)
        or (
            snapshot is not None
            and snapshot.qualification is not None
            and snapshot.qualification.is_qualified
        )
        or packet.is_qualified
    )
    if qualified:
        if not reasons and not unknowns:
            reasons = ["Session priorities introduce material uncertainty."]
        return SessionQualification(
            state="qualified",
            reasons=tuple(reasons),
            material_unknowns=tuple(unknowns),
            could_change_recommendation=reverse,
        )
    return SessionQualification(state="unqualified")


def _recommendation_evidence(packet: DecisionEvidencePacket) -> tuple[str, ...]:
    return tuple(item.evidence_id for item in packet.facts_for("recommendation")[:2]) or (
        "recommendation",
    )


def _price_evidence(packet: DecisionEvidencePacket) -> tuple[str, ...]:
    return tuple(item.evidence_id for item in packet.facts_for("price", "price_state")) or (
        "price",
    )


def _attribute_evidence(
    packet: DecisionEvidencePacket,
    snapshot: CanonicalDecisionSnapshot | None,
    topic: str,
) -> tuple[str, ...]:
    ids: list[str] = []
    if snapshot is not None:
        for item in snapshot.evidence:
            if item.topic.lower() == topic:
                ids.append(item.evidence_id)
        for product in snapshot.product_presentation:
            for attr in product.fit_attributes:
                if attr.key.lower() == topic:
                    ids.extend(attr.evidence_ids)
    ids.extend(item.evidence_id for item in packet.facts if topic in item.topic.lower())
    return tuple(dict.fromkeys(ids)) or (topic,)
