"""Phase 29.4A: answer shopper questions from existing decision evidence only.

Read-only. Does not research, refine recommendations, or mutate snapshots.
"""

# ruff: noqa: E501

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from app.consumer.location import DeliveryContext
from app.consumer.presentation import build_page_view
from app.consumer.pricing import PRICE_STATE_LABELS, format_php
from app.consumer.session_overlay import apply_session_overlay_to_packet
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
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
from app.services.decision_evidence_packet import (
    DecisionEvidencePacket,
    EvaluatedOfferFact,
    packet_from_page_view,
    packet_from_snapshot,
    presentation_fixtures_allowed,
    unavailable_packet,
)

AnswerStatus = Literal[
    "answered",
    "partially_answered",
    "insufficient_evidence",
    "outside_evaluated_set",
    "preference_change_not_applied",
]

QuestionKind = Literal[
    "price",
    "shipping",
    "import",
    "location",
    "recommendation",
    "piqscore",
    "sources",
    "unknowns",
    "qualified",
    "freshness",
    "warranty",
    "voucher",
    "topic",
    "outside_set",
    "preference_change",
    "future_price",
    "shopper",
    "product",
    "offer_url",
    "best_for",
    "tradeoff",
    "fit",
    "general",
]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_OUTSIDE_HINTS = (
    "airpods max",
    "airpods",
    "pixel 9",
    "google pixel",
    "pixel",
)
_SOURCE_HINTS = ("reddit", "youtube", "amazon", "lazada", "shopee", "tiktok")


@dataclass(frozen=True, slots=True)
class EvidenceAnswerResult:
    answer: str
    status: AnswerStatus
    evidence_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    unknowns: tuple[str, ...]
    packet: DecisionEvidencePacket
    kind: QuestionKind


class AnswerFromEvidenceService:
    """Compose truthful answers from a bounded evidence packet."""

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

    def answer(
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
                "decision_id is required to answer from evidence."
            )
        context_version = int(payload.get("context_version") or 1)
        surface = str(payload.get("surface") or "results")
        conversation_id = payload.get("conversation_id")
        page = surface if surface in {"results", "compare", "why"} else "results"

        packet, resolved_snapshot = self._resolve_packet(
            decision_id=decision_id,
            context_version=context_version,
            location=location or DeliveryContext(),
            owner=owner,
            conversation_id=str(conversation_id) if conversation_id else None,
            snapshot=snapshot,
            page=page,  # type: ignore[arg-type]
        )
        overlay = None
        if self._conversations is not None:
            if conversation_id:
                bound = (
                    self._conversations.get_for_owner(str(conversation_id), owner)
                    if owner is not None
                    else self._conversations.get(str(conversation_id))
                )
                overlay = bound.session_refinement if bound is not None else None
            if overlay is None and owner is not None:
                bound = self._conversations.find_bound_for_owner(owner, packet.decision_id)
                overlay = bound.session_refinement if bound is not None else None
        if overlay is not None:
            packet = apply_session_overlay_to_packet(packet, overlay)
        before_digest = resolved_snapshot.content_sha256 if resolved_snapshot else None
        before_rec = resolved_snapshot.recommendation.snapshot_sha256 if resolved_snapshot else None
        before_scores = (
            resolved_snapshot.canonical_piqscore_set_sha256 if resolved_snapshot else None
        )
        before_ids = (
            resolved_snapshot.evaluated_product_ids
            if resolved_snapshot
            else packet.evaluated_product_ids
        )

        result = compose_evidence_answer(question, packet)
        response = self._to_response(question, result, conversation_id=conversation_id)

        if resolved_snapshot is not None and (
            resolved_snapshot.content_sha256 != before_digest
            or resolved_snapshot.recommendation.snapshot_sha256 != before_rec
            or resolved_snapshot.canonical_piqscore_set_sha256 != before_scores
            or resolved_snapshot.evaluated_product_ids != before_ids
        ):
            raise DecisionSnapshotIntegrityError(decision_id, context_version)

        if self._conversations is not None and conversation_id and owner is not None:
            self._append_bound_turn(
                conversation_id=str(conversation_id),
                owner=owner,
                question=question,
                packet=packet,
                result=result,
            )
        return response

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

    def _append_bound_turn(
        self,
        *,
        conversation_id: str,
        owner: ConversationOwner,
        question: str,
        packet: DecisionEvidencePacket,
        result: EvidenceAnswerResult,
    ) -> None:
        if self._conversations is None:
            return
        context = self._conversations.get_for_owner(conversation_id, owner)
        if context is None or context.decision_context is None:
            return
        allowed = context.decision_context.evaluated_product_ids
        cited = tuple(item for item in result.product_ids if item in allowed) or allowed
        now = self._clock()
        user_turn = ConversationTurn(
            role="user",
            intent="general",
            product_ids=cited,
            product_names=(),
            query=question,
            created_at=now,
            turn_id=self._id_factory(),
            decision_id=context.decision_context.decision_id,
            context_version=context.decision_context.context_version,
            action="answer_from_evidence",
        )
        self._conversations.append_turn(
            conversation_id,
            user_turn,
            last_intent="general",
            last_product_ids=allowed,
            last_product_names=context.last_product_names,
        )

    def _to_response(
        self,
        question: str,
        result: EvidenceAnswerResult,
        *,
        conversation_id: str | None,
    ) -> ShoppingAssistantResponse:
        packet = result.packet
        evidence = tuple(
            ShoppingEvidence(
                evidence_id=item.evidence_id,
                type=_evidence_type(item.topic),
                source_id=item.source or "decision-evidence",
                description=item.fact,
                product_id=item.product_id,
                value=None,
            )
            for item in packet.facts
            if item.evidence_id in result.evidence_ids
        )
        if not evidence and result.evidence_ids:
            evidence = tuple(
                ShoppingEvidence(
                    evidence_id=item_id,
                    type="recommendation",
                    source_id="decision-evidence",
                    description=result.answer,
                    product_id=None,
                )
                for item_id in result.evidence_ids
            )
        warnings: list[AssistantWarning] = []
        if result.status in {"insufficient_evidence", "outside_evaluated_set"}:
            warnings.append(
                AssistantWarning(
                    message="This answer uses only evidence already captured for the current decision.",
                    code="evidence_bound",
                )
            )
        if result.status == "preference_change_not_applied":
            warnings.append(
                AssistantWarning(
                    message="The Recommendation was not changed.",
                    code="recommendation_not_mutated",
                )
            )
        band = {
            "answered": "High",
            "partially_answered": "Medium",
            "insufficient_evidence": "Low",
            "outside_evaluated_set": "Low",
            "preference_change_not_applied": "Medium",
        }[result.status]
        score = {"High": 0.82, "Medium": 0.55, "Low": 0.28}[band]
        return ShoppingAssistantResponse(
            query=question,
            intent="general",
            answer=result.answer,
            top_recommendation=None,
            alternatives=(),
            evidence=evidence,
            warnings=tuple(warnings),
            data_status="mock"
            if packet.data_classification == "non_live_contract_fixture"
            else "imported",
            providers_used=("answer_from_evidence",),
            fallback_used=True,
            confidence=AssistantConfidence(score=score, band=band, factors=("existing_evidence",)),
            mode="economy",
            conversation_id=conversation_id,
            processing={
                "action": "answer_from_evidence",
                "answer_status": result.status,
                "response_source": "existing_evidence",
                "requires_research_confirmation": False,
                "affiliate_influence": False,
                "data_classification": packet.data_classification,
                "decision_id": packet.decision_id,
                "context_version": packet.context_version,
                "evidence_ids": list(result.evidence_ids),
                "canonical_piqscore_snapshot_sha256": packet.canonical_piqscore_set_sha256,
                "prompts_included": False,
                "secrets_included": False,
            },
            generated_at=self._clock(),
        )


def compose_evidence_answer(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    kind = classify_question(question, packet)
    if not packet.available:
        return EvidenceAnswerResult(
            answer=(
                "Offer details for this decision are not available. "
                "PiqSavi will not invent prices, merchants, shipping, or Recommendation evidence."
            ),
            status="insufficient_evidence",
            evidence_ids=("unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind=kind,
        )
    handlers = {
        "outside_set": _answer_outside_set,
        "preference_change": _answer_preference,
        "future_price": _answer_future_price,
        "sources": _answer_sources,
        "unknowns": _answer_unknowns,
        "qualified": _answer_qualified,
        "piqscore": _answer_piqscore,
        "recommendation": _answer_recommendation,
        "shipping": _answer_shipping,
        "import": _answer_import,
        "location": _answer_location,
        "price": _answer_price,
        "voucher": _answer_voucher,
        "warranty": _answer_warranty,
        "freshness": _answer_freshness,
        "shopper": _answer_shopper,
        "product": _answer_product,
        "offer_url": _answer_offer_url,
        "best_for": _answer_best_for,
        "tradeoff": _answer_tradeoff,
        "fit": _answer_fit,
        "topic": _answer_topic,
        "general": _answer_general,
    }
    return handlers[kind](question, packet)


def classify_question(question: str, packet: DecisionEvidencePacket) -> QuestionKind:
    text = question.lower()
    if _mentions_outside_product(text, packet):
        return "outside_set"
    if _is_preference_change(text):
        return "preference_change"
    if any(
        phrase in text
        for phrase in (
            "next month",
            "11.11",
            "cheaper later",
            "will this be cheaper",
            "future price",
            "drop in price",
            "sale next",
        )
    ):
        return "future_price"
    if (
        any(hint in text for hint in _SOURCE_HINTS)
        or "source" in text
        or "checked" in text
        or "did you check" in text
    ):
        return "sources"
    if "qualified" in text:
        return "qualified"
    if "piqscore" in text or "higher score" in text or "objective score" in text:
        return "piqscore"
    if any(
        phrase in text
        for phrase in (
            "best piq",
            "why is this best",
            "why did this beat",
            "why not",
            "why did sony",
            "why did bose",
            "why this recommendation",
            "why did you switch",
            "why are you still",
            "why didn't it change",
            "why didnt it change",
        )
    ):
        return "recommendation"
    if "warranty" in text:
        return "warranty"
    if "voucher" in text or "discount" in text:
        return "voucher"
    if "import" in text or "landed" in text or "customs" in text or "duties" in text:
        return "import"
    if "shipping" in text or "include shipping" in text:
        return "shipping"
    if (
        "what location" in text
        or "deliver" in text
        or "taguig" in text
        or "cebu" in text
        or "davao" in text
    ):
        return "location"
    if (
        "don't you know" in text
        or "do not know" in text
        or "unknowns" in text
        or "what don’t you know" in text
    ):
        return "unknowns"
    if "fresh" in text or "when did you check" in text or "how old" in text:
        return "freshness"
    if any(
        phrase in text
        for phrase in (
            "where can i buy",
            "where can I buy",
            "view offer",
            "offer url",
            "offer link",
            "buy this",
        )
    ):
        return "offer_url"
    if (
        "trade-off" in text
        or "tradeoff" in text
        or "when would" in text
        or "when an alternative" in text
    ):
        return "tradeoff"
    if "what is this best for" in text or "best for" in text:
        return "best_for"
    if any(
        phrase in text
        for phrase in (
            "top priority",
            "my budget",
            "did i say",
            "what did i say",
            "what was my",
            "use case",
        )
    ):
        return "shopper"
    if "which model" in text or "what model" in text or "what brand" in text:
        return "product"
    if "multipoint" in text or "does it support" in text or "fit attribute" in text:
        return "fit"
    if "price" in text or "₱" in question or "cost" in text or "how much" in text:
        return "price"
    topics = {item.topic.lower() for item in packet.facts}
    for topic in topics:
        if topic and topic in text:
            return "topic"
    return "general"


def _mentions_outside_product(text: str, packet: DecisionEvidencePacket) -> bool:
    evaluated = " ".join(packet.names()).lower() + " " + " ".join(packet.evaluated_product_ids)
    return any(hint in text and hint not in evaluated for hint in _OUTSIDE_HINTS)


def _is_preference_change(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "matters more",
            "matter more",
            "i prefer",
            "priority is now",
            "change my recommendation",
            "update the recommendation",
            "comfort matters",
        )
    )


def _best(packet: DecisionEvidencePacket) -> EvaluatedOfferFact | None:
    return packet.offer(packet.best_piq_product_id) or (packet.offers[0] if packet.offers else None)


def _cite(*facts) -> tuple[str, ...]:  # noqa: ANN001
    return tuple(item.evidence_id for item in facts if item is not None)


def _evidence_type(topic: str) -> str:
    return {
        "price": "price",
        "price_state": "price",
        "voucher": "price",
        "shipping": "price",
        "import": "price",
        "tax": "price",
        "piqscore": "deal_score",
        "merchant": "seller",
        "recommendation": "recommendation",
        "qualified": "recommendation",
        "source": "review",
        "location": "recommendation",
        "unknown": "review",
        "freshness": "review",
    }.get(topic, "review")


def _answer_outside_set(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    mentioned = next((hint for hint in _OUTSIDE_HINTS if hint in question.lower()), "that product")
    names = ", ".join(packet.names()) or "the current evaluated offers"
    return EvidenceAnswerResult(
        answer=(
            f"{mentioned.title()} was not among the offers evaluated for this decision. "
            f"PiqSavi can only explain {names} from the evidence already captured. "
            "No new product search was started."
        ),
        status="outside_evaluated_set",
        evidence_ids=_cite(*packet.facts[:1]) or ("evaluated-set",),
        product_ids=packet.evaluated_product_ids,
        unknowns=packet.unknowns,
        packet=packet,
        kind="outside_set",
    )


def _answer_preference(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    name = packet.best_piq_name or "the current Best Piq for You"
    return EvidenceAnswerResult(
        answer=(
            f"A new priority could change which option is Best Piq for You, but PiqSavi "
            f"has not changed the Recommendation. {name} remains the current Best Piq "
            "from the existing evidence. Preference refinement is not applied in this step."
        ),
        status="preference_change_not_applied",
        evidence_ids=_cite(*packet.facts_for("recommendation")[:1]) or ("recommendation",),
        product_ids=(best.product_id,) if best else (),
        unknowns=packet.unknowns,
        packet=packet,
        kind="preference_change",
    )


def _answer_future_price(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    return EvidenceAnswerResult(
        answer=(
            "The current decision does not contain evidence about future prices or upcoming "
            "promotions, so PiqSavi cannot predict whether this will be cheaper later. "
            "No additional research was started."
        ),
        status="insufficient_evidence",
        evidence_ids=_cite(*packet.facts_for("unknown")[:1]) or ("timing-unknown",),
        product_ids=(),
        unknowns=packet.unknowns + ("future prices are not in this decision",),
        packet=packet,
        kind="future_price",
    )


def _answer_sources(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    text = question.lower()
    asked = [hint for hint in _SOURCE_HINTS if hint in text]
    used = {item.lower() for item in packet.sources}
    facts = packet.facts_for("source")
    if asked:
        missing = [name for name in asked if not any(name in source for source in used)]
        if missing:
            listed = ", ".join(packet.sources) if packet.sources else "none listed"
            return EvidenceAnswerResult(
                answer=(
                    f"{missing[0].title()} is not listed among the sources used for this decision. "
                    f"Sources shown for this decision: {listed}."
                ),
                status="answered",
                evidence_ids=_cite(*facts) or ("sources",),
                product_ids=(),
                unknowns=packet.unknowns,
                packet=packet,
                kind="sources",
            )
        return EvidenceAnswerResult(
            answer=f"{asked[0].title()} is listed among the sources used for this decision.",
            status="answered",
            evidence_ids=_cite(*facts) or ("sources",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="sources",
        )
    if not packet.sources:
        return EvidenceAnswerResult(
            answer="This decision does not list the sources that were used.",
            status="insufficient_evidence",
            evidence_ids=("sources-unknown",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="sources",
        )
    listed = ", ".join(packet.sources)
    return EvidenceAnswerResult(
        answer=f"Sources used for this decision: {listed}. PiqSavi did not check every major platform.",
        status="answered",
        evidence_ids=_cite(*facts) or ("sources",),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="sources",
    )


def _answer_unknowns(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    if not packet.unknowns:
        return EvidenceAnswerResult(
            answer="This decision does not list additional explicit unknowns.",
            status="partially_answered",
            evidence_ids=_cite(*packet.facts[:1]) or ("unknowns",),
            product_ids=(),
            unknowns=(),
            packet=packet,
            kind="unknowns",
        )
    listed = " ".join(packet.unknowns)
    return EvidenceAnswerResult(
        answer=f"What remains unknown for this decision: {listed}",
        status="answered",
        evidence_ids=_cite(*packet.facts_for("unknown")) or ("unknowns",),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="unknowns",
    )


def _answer_qualified(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    if packet.qualification_state is None:
        return EvidenceAnswerResult(
            answer=(
                "Qualification status was not captured for this decision. "
                "PiqSavi will not treat a missing qualification field as an explicit "
                "unqualified Recommendation."
            ),
            status="insufficient_evidence",
            evidence_ids=("qualification-not-captured",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="qualified",
        )
    if packet.qualification_state == "unqualified" or not packet.is_qualified:
        return EvidenceAnswerResult(
            answer=(
                f"{packet.best_piq_name} is the current Best Piq for You and is not marked as "
                "qualified. The captured Recommendation remains fully asserted from existing evidence."
            ),
            status="answered",
            evidence_ids=_cite(*packet.facts_for("recommendation")[:1]) or ("recommendation",),
            product_ids=(best.product_id,) if best else (),
            unknowns=packet.unknowns,
            packet=packet,
            kind="qualified",
        )
    reason = packet.qualified_reason or "A material unknown remains in the captured evidence."
    return EvidenceAnswerResult(
        answer=(
            f"This is a qualified Best Piq for You. {reason} "
            f"{packet.best_piq_name} remains the strongest supported option from the evaluated "
            "offers, but delivered economics could change. The qualification has not been removed."
        ),
        status="partially_answered",
        evidence_ids=_cite(*packet.facts_for("qualified", "shipping", "unknown")[:3])
        or ("qualified",),
        product_ids=(best.product_id,) if best else (),
        unknowns=packet.unknowns,
        packet=packet,
        kind="qualified",
    )


def _answer_piqscore(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    highest = packet.offer(packet.highest_piqscore_product_id)
    facts = packet.facts_for("piqscore")
    if best is None or best.piqscore is None:
        return EvidenceAnswerResult(
            answer="This decision does not include PiqScore values that PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("piqscore-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="piqscore",
        )
    if (
        highest is not None
        and highest.product_id != best.product_id
        and highest.piqscore is not None
    ):
        answer = (
            f"{highest.display_name} has the higher objective PiqScore "
            f"({highest.piqscore}) and {best.display_name} is Best Piq for You "
            f"(PiqScore {best.piqscore}). PiqScore evaluates the offer; Best Piq for You "
            "reflects what best fits the shopper. Personalization did not rewrite either PiqScore."
        )
        return EvidenceAnswerResult(
            answer=answer,
            status="answered",
            evidence_ids=_cite(*facts[:4]) or ("piqscore",),
            product_ids=(best.product_id, highest.product_id),
            unknowns=packet.unknowns,
            packet=packet,
            kind="piqscore",
        )
    return EvidenceAnswerResult(
        answer=(
            f"{best.display_name} has PiqScore {best.piqscore} and is also Best Piq for You. "
            "PiqScore evaluates the offer; it is not a personalized score."
        ),
        status="answered",
        evidence_ids=_cite(*facts[:2]) or ("piqscore",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="piqscore",
    )


def _answer_recommendation(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    facts = packet.facts_for("recommendation", "piqscore")
    if best is None:
        return EvidenceAnswerResult(
            answer="This decision does not include Recommendation reasoning PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("recommendation-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="recommendation",
        )
    reasons = " ".join(best.why_it_won) if best.why_it_won else ""
    fit = next(
        (
            item.fact
            for item in packet.facts_for("recommendation")
            if "budget" in item.fact.lower() or "fits" in item.fact.lower()
        ),
        "",
    )
    extra = f" {reasons}".rstrip()
    if fit:
        extra = f" {fit}{extra}"
    qualified = ""
    if packet.is_qualified:
        qualified = (
            f" This remains a qualified Recommendation. {packet.qualified_reason or ''}".rstrip()
        )
    alt = ""
    mentioned_alt = next(
        (
            item
            for item in packet.offers
            if not item.is_best_piq and item.display_name.split()[0].lower() in question.lower()
        ),
        None,
    )
    if mentioned_alt and mentioned_alt.alternative_reason:
        alt = f" {mentioned_alt.display_name} was not selected: {mentioned_alt.alternative_reason}"
    session = next(
        (item.fact for item in packet.facts if item.evidence_id == "session-current-best"),
        "",
    )
    historical = next(
        (item.fact for item in packet.facts if item.evidence_id == "session-original-best"),
        "",
    )
    session_note = ""
    if session:
        session_note = f" {session}"
        if historical:
            session_note += f" {historical}"
        if "why did you switch" in question.lower() or "why are you still" in question.lower():
            session_note += " " + " ".join(
                item.fact for item in packet.facts if item.evidence_id.startswith("session-reason:")
            )
    return EvidenceAnswerResult(
        answer=(
            f"{best.display_name} is Best Piq for You from the evaluated offers.{extra}{alt}"
            f"{session_note}{qualified} PiqScore itself is not personalized."
        ).strip(),
        status="partially_answered" if packet.is_qualified else "answered",
        evidence_ids=_cite(*facts[:6]) or ("recommendation",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="recommendation",
    )


def _answer_shipping(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    facts = packet.facts_for("shipping", "price_state", "location")
    if best is None or best.shipping_status is None:
        return EvidenceAnswerResult(
            answer="This decision does not include shipping evidence PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("shipping-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns + ("shipping evidence is not in this decision",),
            packet=packet,
            kind="shipping",
        )
    dest = packet.delivery_label or "the current delivery area"
    if best.shipping_status in {"unknown", "unverified"} or best.shipping_display in {
        "Not verified",
        "Unknown",
    }:
        label = best.price_label or PRICE_STATE_LABELS["price_before_shipping"]
        amount = format_php(best.price_amount)
        return EvidenceAnswerResult(
            answer=(
                f"Shipping to {dest} is not verified, so it is not treated as FREE. "
                f"The shown {label} is {amount}. Unknown shipping stays unknown."
            ),
            status="partially_answered",
            evidence_ids=_cite(*facts[:4]) or ("shipping",),
            product_ids=(best.product_id,),
            unknowns=packet.unknowns,
            packet=packet,
            kind="shipping",
        )
    return EvidenceAnswerResult(
        answer=(
            f"For {dest}, captured shipping for {best.display_name} is {best.shipping_display}. "
            f"The {best.price_label} is {format_php(best.price_amount)}."
        ),
        status="answered",
        evidence_ids=_cite(*facts[:4]) or ("shipping",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="shipping",
    )


def _answer_import(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    facts = packet.facts_for("import", "price_state", "tax")
    if best is None or best.import_status is None:
        return EvidenceAnswerResult(
            answer="This decision does not include import-charge evidence PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("import-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="import",
        )
    if best.import_status in {"unknown", "unverified"}:
        return EvidenceAnswerResult(
            answer=(
                f"Import charges for {best.display_name} are {best.import_status}, so landed cost "
                f"is not complete. The current {best.price_label} is {format_php(best.price_amount)}. "
                "Unverified import charges are not treated as zero or guaranteed."
            ),
            status="partially_answered",
            evidence_ids=_cite(*facts[:3]) or ("import",),
            product_ids=(best.product_id,),
            unknowns=packet.unknowns,
            packet=packet,
            kind="import",
        )
    estimated = "estimated " if best.import_status == "estimated" else ""
    return EvidenceAnswerResult(
        answer=(
            f"{best.display_name} uses {best.price_label} {format_php(best.price_amount)}. "
            f"Import charges in this decision are {estimated}{best.import_status} and are not "
            "a guaranteed checkout amount."
        ),
        status="answered",
        evidence_ids=_cite(*facts[:3]) or ("import",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="import",
    )


def _answer_location(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("location", "shipping")
    current = packet.delivery_label
    hypothetical = any(phrase in question.lower() for phrase in ("what if", "instead", "switch to"))
    if hypothetical:
        dest = current or "the current delivery area"
        return EvidenceAnswerResult(
            answer=(
                f"This decision was evaluated for {dest}. Another destination can change shipping "
                "and delivered cost, and might change the Recommendation. PiqSavi did not reprice "
                "or change Best Piq for You for a different destination in this answer."
            ),
            status="partially_answered",
            evidence_ids=_cite(*facts[:2]) or ("location",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="location",
        )
    if not current:
        return EvidenceAnswerResult(
            answer="No delivery location is set for this decision, so location-specific shipping is unknown.",
            status="partially_answered",
            evidence_ids=_cite(*facts[:1]) or ("location",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="location",
        )
    verified = "verified" if packet.delivery_verified else "not yet verified"
    return EvidenceAnswerResult(
        answer=f"The current delivery area is {current}. Shipping for this area is {verified}.",
        status="answered" if packet.delivery_verified else "partially_answered",
        evidence_ids=_cite(*facts[:2]) or ("location",),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="location",
    )


def _answer_price(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    facts = packet.facts_for("price", "price_state", "voucher", "shipping")
    if best is None or best.price_state is None:
        return EvidenceAnswerResult(
            answer="This decision does not include offer price evidence PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("price-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="price",
        )
    listing = next(
        (item.fact for item in packet.facts_for("price") if item.product_id == best.product_id), ""
    )
    voucher_fact = next(
        (item for item in packet.facts_for("voucher") if item.product_id == best.product_id),
        None,
    )
    voucher_note = ""
    if voucher_fact and voucher_fact.status in {"unverified", "expired", "unsupported"}:
        voucher_note = (
            f" A {voucher_fact.status} voucher is present and was not treated as an applied saving."
        )
    elif voucher_fact and voucher_fact.status == "verified":
        voucher_note = f" {voucher_fact.fact}."
    return EvidenceAnswerResult(
        answer=(
            f"{best.display_name} is shown as {best.price_label} {format_php(best.price_amount)}. "
            f"{listing}.{voucher_note} These values come from the current decision evidence, "
            "not from a new price calculation."
        ).strip(),
        status="answered",
        evidence_ids=_cite(*facts[:6]) or ("price",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="price",
    )


def _answer_voucher(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    facts = packet.facts_for("voucher", "price_state")
    voucher = next((item for item in facts if item.topic == "voucher"), None)
    if voucher is None:
        return EvidenceAnswerResult(
            answer="This decision does not include voucher evidence PiqSavi can explain.",
            status="insufficient_evidence",
            evidence_ids=("voucher-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="voucher",
        )
    if voucher.status in {"unverified", "expired", "unsupported"}:
        return EvidenceAnswerResult(
            answer=(
                f"{voucher.fact}. That saving is not treated as currently applied to the shown price."
            ),
            status="answered",
            evidence_ids=_cite(voucher),
            product_ids=(best.product_id,) if best else (),
            unknowns=packet.unknowns,
            packet=packet,
            kind="voucher",
        )
    return EvidenceAnswerResult(
        answer=voucher.fact,
        status="answered",
        evidence_ids=_cite(voucher),
        product_ids=(best.product_id,) if best else (),
        unknowns=packet.unknowns,
        packet=packet,
        kind="voucher",
    )


def _answer_warranty(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = tuple(
        item
        for item in packet.facts
        if "warrant" in item.topic.lower() or "warrant" in item.fact.lower()
    )
    if not facts:
        return EvidenceAnswerResult(
            answer=(
                "This decision does not contain warranty evidence, including whether any "
                "international warranty is valid in the Philippines. That remains unknown."
            ),
            status="insufficient_evidence",
            evidence_ids=("warranty-unknown",),
            product_ids=(),
            unknowns=packet.unknowns + ("warranty applicability is not in this decision",),
            packet=packet,
            kind="warranty",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in facts),
        status="partially_answered",
        evidence_ids=_cite(*facts),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="warranty",
    )


def _answer_freshness(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("freshness")
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include a check time or freshness timestamp PiqSavi can report.",
            status="insufficient_evidence",
            evidence_ids=("freshness-unknown",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="freshness",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in facts[:3]),
        status="answered",
        evidence_ids=_cite(*facts[:3]),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="freshness",
    )


def _answer_shopper(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for(
        "shopper", "budget", "priority", "use_case", "urgency", "required_feature"
    )
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include the original shopper context PiqSavi used.",
            status="insufficient_evidence",
            evidence_ids=("shopper-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="shopper",
        )
    specific = tuple(item for item in facts if item.topic != "shopper")
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in (specific or facts)),
        status="answered",
        evidence_ids=_cite(*facts),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="shopper",
    )


def _answer_product(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("brand", "model", "category")
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include structured product identity beyond the evaluated display names.",
            status="insufficient_evidence",
            evidence_ids=("product-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="product",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in facts),
        status="answered",
        evidence_ids=_cite(*facts),
        product_ids=tuple(item.product_id for item in facts if item.product_id),
        unknowns=packet.unknowns,
        packet=packet,
        kind="product",
    )


def _answer_offer_url(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("offer_url")
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include a canonical outbound offer destination.",
            status="insufficient_evidence",
            evidence_ids=("offer-url-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="offer_url",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in facts),
        status="answered",
        evidence_ids=_cite(*facts),
        product_ids=tuple(item.product_id for item in facts if item.product_id),
        unknowns=packet.unknowns,
        packet=packet,
        kind="offer_url",
    )


def _answer_best_for(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("best_for")
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include a captured Best-for conclusion.",
            status="insufficient_evidence",
            evidence_ids=("best-for-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="best_for",
        )
    return EvidenceAnswerResult(
        answer="This Recommendation is best for: " + "; ".join(item.fact for item in facts) + ".",
        status="answered",
        evidence_ids=_cite(*facts),
        product_ids=(),
        unknowns=packet.unknowns,
        packet=packet,
        kind="best_for",
    )


def _answer_tradeoff(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("tradeoff")
    if not facts:
        return EvidenceAnswerResult(
            answer="This decision does not include captured alternative trade-off reasoning.",
            status="insufficient_evidence",
            evidence_ids=("tradeoff-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="tradeoff",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in facts),
        status="answered",
        evidence_ids=_cite(*facts),
        product_ids=tuple(item.product_id for item in facts if item.product_id),
        unknowns=packet.unknowns,
        packet=packet,
        kind="tradeoff",
    )


def _answer_fit(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    facts = packet.facts_for("fit")
    text = question.lower()
    matched = tuple(
        item for item in facts if any(part in item.fact.lower() for part in text.split())
    )
    chosen = matched or facts
    if not chosen:
        return EvidenceAnswerResult(
            answer="This decision does not include captured product-fit attributes.",
            status="insufficient_evidence",
            evidence_ids=("fit-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="fit",
        )
    return EvidenceAnswerResult(
        answer=" ".join(item.fact for item in chosen),
        status="answered",
        evidence_ids=_cite(*chosen),
        product_ids=tuple(item.product_id for item in chosen if item.product_id),
        unknowns=packet.unknowns,
        packet=packet,
        kind="fit",
    )


def _answer_topic(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    text = question.lower()
    matched = tuple(item for item in packet.facts if item.topic.lower() in text)
    if not matched:
        return _answer_general(question, packet)
    names = {item.product_id: item for item in packet.offers}
    lines = []
    for item in matched:
        offer = names.get(item.product_id or "")
        label = offer.display_name if offer else item.product_id or "this decision"
        lines.append(f"{label}: {item.fact}")
    return EvidenceAnswerResult(
        answer=" ".join(lines),
        status="answered",
        evidence_ids=_cite(*matched),
        product_ids=tuple(item.product_id for item in matched if item.product_id),
        unknowns=packet.unknowns,
        packet=packet,
        kind="topic",
    )


def _answer_general(question: str, packet: DecisionEvidencePacket) -> EvidenceAnswerResult:
    best = _best(packet)
    if best is None:
        return EvidenceAnswerResult(
            answer="The current decision does not contain evidence that answers this question.",
            status="insufficient_evidence",
            evidence_ids=("general-unavailable",),
            product_ids=(),
            unknowns=packet.unknowns,
            packet=packet,
            kind="general",
        )
    return EvidenceAnswerResult(
        answer=(
            f"{best.display_name} is Best Piq for You in this decision. "
            "Ask about shipping, price, sources, PiqScore, or what remains unknown "
            "and PiqSavi will explain from the evidence already captured."
        ),
        status="partially_answered",
        evidence_ids=_cite(*packet.facts_for("recommendation", "piqscore")[:2]) or ("general",),
        product_ids=(best.product_id,),
        unknowns=packet.unknowns,
        packet=packet,
        kind="general",
    )
