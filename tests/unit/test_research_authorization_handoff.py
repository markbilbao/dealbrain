"""Research Authorization / Execution Handoff Contract tests.

Authorization is created from explicit confirmation. Live research does not run.
"""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.core.dependencies import get_shopping_decision_snapshot_repository
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import ShoppingAssistantNotFoundError, ShoppingAssistantValidationError
from app.main import create_app
from app.services.decision_evidence_packet import packet_from_snapshot, unavailable_packet
from app.services.propose_research import (
    compose_research_proposal,
    confirmation_applies_to_proposal,
    confirmation_correlation,
    is_explicit_confirmation,
)
from app.services.research_authorization import (
    create_research_authorization_from_proposal,
    derive_authorization_idempotency_key,
    get_authorized_research_handoff,
    load_research_authorization_for_owner,
    mark_research_authorization_consumed,
    validate_research_authorization_for_execution,
)
from httpx import ASGITransport, AsyncClient

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    BOSE_ID,
    DECISION_ID,
    SENN_ID,
    SONY_ID,
    START,
    _owner,
    _presentation,
)
from tests.unit.test_phase_29_4c_propose_research import _assistant, _service

AUTH_HTTP_DECISION_ID = "00000000-0000-4000-8000-00000000029d"

ROOT = Path(__file__).resolve().parents[2]


def _confirm(service, first, query="Yes, research that", *, bind=True, **extra):
    payload = {
        "query": query,
        "decision_id": DECISION_ID,
        "conversation_id": first.conversation_id,
        **extra,
    }
    if bind:
        payload.setdefault("proposal_id", first.processing["proposal_id"])
        payload.setdefault("proposal_version", first.processing["proposal_version"])
    return service.handle(payload, owner=_owner(), snapshot=_presentation())


def test_explicit_confirmation_creates_bound_authorization() -> None:
    service, snapshots, conversations, snapshot = _service()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
        snapshot.offer_economics,
    )
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first, "Yes, research AirPods Max.")
    assert confirmed is not None
    assert confirmed.processing["authorization_created"] is True
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert confirmed.processing["execution_available"] is False
    assert confirmed.processing["execution_started"] is False
    assert confirmed.processing["research_executed"] is False
    assert confirmed.processing["affiliate_influence"] is False
    auth_id = confirmed.processing["research_authorization_id"]
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    assert auth.authorization_id == auth_id
    assert auth.conversation_id == first.conversation_id
    assert auth.decision_id == DECISION_ID
    assert auth.canonical_context_version == 1
    assert auth.proposal_id == first.processing["proposal_id"]
    assert auth.proposal_version == first.processing["proposal_version"]
    assert "AirPods Max" in auth.scope.outside_set_product_names
    assert "usb-c" not in " ".join(auth.scope.outside_set_product_names).lower()
    assert auth.idempotency_key.startswith("research-auth:")
    assert context.research_proposal is not None
    assert context.research_proposal.status == (
        "research_confirmation_received_but_execution_unavailable"
    )
    assert context.research_proposal.is_pending is False
    assert context.research_proposal.authorization_id == auth_id
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == before[0]
    assert loaded.canonical_piqscore_set_sha256 == before[1]
    assert loaded.recommendation.snapshot_sha256 == before[2]
    assert loaded.evaluated_product_ids == before[3]
    assert loaded.recommendation.best_piq_product_id == before[4]
    assert loaded.offer_economics == before[5]


def test_repeat_confirmation_reuses_same_authorization() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    once = _confirm(service, first)
    twice = _confirm(service, first)
    assert once is not None and twice is not None
    assert (
        once.processing["research_authorization_id"]
        == twice.processing["research_authorization_id"]
    )
    assert twice.processing["authorization_created"] is False
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert len(context.research_authorizations) == 1
    different_token = _confirm(service, first, confirmation_token="browser-token-2")
    assert different_token is not None
    assert (
        different_token.processing["research_authorization_id"]
        == once.processing["research_authorization_id"]
    )


def test_distinct_proposal_versions_get_distinct_authorizations() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    airpods = _confirm(service, first)
    beats = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert beats is not None
    beats_auth = _confirm(service, beats, "Yes, research Beats Studio Pro.")
    assert airpods is not None and beats_auth is not None
    assert (
        airpods.processing["research_authorization_id"]
        != beats_auth.processing["research_authorization_id"]
    )
    context = conversations.get(first.conversation_id)
    assert context is not None
    ids = {item.authorization_id for item in context.research_authorizations}
    assert len(ids) == 2
    previous = next(
        item
        for item in context.research_authorizations
        if item.authorization_id == airpods.processing["research_authorization_id"]
    )
    assert previous.status == "invalidated"


def test_wrong_owner_cannot_authorize_inspect_cancel_or_validate() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    stranger = ConversationOwner(
        principal_type="guest",
        principal_id="other-guest",
        session_id="session-other-guest",
        expires_at=START + timedelta(minutes=30),
    )
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.handle(
            {
                "query": "Yes, research that",
                "decision_id": DECISION_ID,
                "conversation_id": first.conversation_id,
                "proposal_id": first.processing["proposal_id"],
                "proposal_version": first.processing["proposal_version"],
            },
            owner=stranger,
        )
    confirmed = _confirm(service, first)
    assert confirmed is not None
    auth_id = confirmed.processing["research_authorization_id"]
    assert conversations.get_for_owner(first.conversation_id, stranger) is None
    with pytest.raises(ShoppingAssistantNotFoundError):
        load_research_authorization_for_owner(
            conversations,
            authorization_id=auth_id,
            owner=stranger,
            conversation_id=first.conversation_id,
        )
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.handle(
            {
                "query": "Never mind.",
                "decision_id": DECISION_ID,
                "conversation_id": first.conversation_id,
            },
            owner=stranger,
        )
    context = conversations.get(first.conversation_id)
    assert context is not None
    stolen = context.research_authorization
    assert stolen is not None
    with pytest.raises(ShoppingAssistantNotFoundError):
        validate_research_authorization_for_execution(
            stolen,
            owner=stranger,
            conversation_id=first.conversation_id,
            decision_id=DECISION_ID,
            canonical_context_version=1,
        )


def test_stale_proposal_confirmation_fails_closed() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    v1 = first.processing["proposal_id"]
    v1_version = first.processing["proposal_version"]
    second = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert second is not None
    stale_named = _confirm(service, first, "Yes, research AirPods Max.")
    assert stale_named is not None
    assert stale_named.processing["answer_status"] == "stale_research_proposal"
    assert "research_authorization_id" not in stale_named.processing
    stale_id = service.handle(
        {
            "query": "Yes, research that",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
            "proposal_id": v1,
            "proposal_version": v1_version,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert stale_id is not None
    assert stale_id.processing["answer_status"] == "stale_research_proposal"
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.status == "pending_confirmation"
    assert context.research_proposal.proposal_id == second.processing["proposal_id"]
    assert "Beats Studio Pro" in context.research_proposal.outside_set_product_names
    assert context.research_authorizations == ()


def test_stale_rendered_confirmation_does_not_authorize_replacement() -> None:
    service, snapshots, conversations, snapshot = _service()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
    )
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    airpods_id = first.processing["proposal_id"]
    airpods_version = first.processing["proposal_version"]
    beats = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert beats is not None
    delayed = service.handle(
        {
            "query": "Go ahead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
            "proposal_id": airpods_id,
            "proposal_version": airpods_version,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert delayed is not None
    assert delayed.processing["answer_status"] == "stale_research_proposal"
    assert "research_authorization_id" not in delayed.processing
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorizations == ()
    assert context.research_proposal is not None
    assert context.research_proposal.proposal_id == beats.processing["proposal_id"]
    assert context.research_proposal.status == "pending_confirmation"
    assert "Beats Studio Pro" in context.research_proposal.outside_set_product_names
    assert "AirPods Max" not in context.research_proposal.outside_set_product_names
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == before[0]
    assert loaded.canonical_piqscore_set_sha256 == before[1]
    assert loaded.recommendation.snapshot_sha256 == before[2]
    assert loaded.evaluated_product_ids == before[3]
    assert loaded.recommendation.best_piq_product_id == before[4]


def test_missing_proposal_correlation_does_not_authorize() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    generic = _confirm(service, first, "Go ahead.", bind=False)
    assert generic is not None
    assert generic.processing["answer_status"] == "pending_confirmation"
    assert "research_authorization_id" not in generic.processing
    named = _confirm(service, first, "Yes, research AirPods Max.", bind=False)
    assert named is not None
    assert named.processing["answer_status"] == "pending_confirmation"
    assert "research_authorization_id" not in named.processing
    token_only = _confirm(
        service,
        first,
        "Yes, research that",
        bind=False,
        confirmation_token="browser-token",
    )
    assert token_only is not None
    assert token_only.processing["answer_status"] == "pending_confirmation"
    assert "research_authorization_id" not in token_only.processing
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.status == "pending_confirmation"
    assert context.research_proposal.proposal_id == first.processing["proposal_id"]
    assert context.research_authorizations == ()


def test_stale_proposal_version_fails_closed() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    beats = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert beats is not None
    stale_version = _confirm(service, beats, proposal_version=1)
    assert stale_version is not None
    assert stale_version.processing["answer_status"] == "stale_research_proposal"
    assert "research_authorization_id" not in stale_version.processing
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorizations == ()
    assert context.research_proposal is not None
    assert context.research_proposal.status == "pending_confirmation"
    assert context.research_proposal.proposal_id == beats.processing["proposal_id"]


def test_wrong_proposal_id_does_not_redirect() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    wrong = _confirm(service, first, proposal_id="00000000-0000-4000-8000-00000000beef")
    assert wrong is not None
    assert wrong.processing["answer_status"] == "stale_research_proposal"
    assert "research_authorization_id" not in wrong.processing
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorizations == ()
    assert context.research_proposal is not None
    assert context.research_proposal.proposal_id == first.processing["proposal_id"]
    assert context.research_proposal.status == "pending_confirmation"


def test_wrong_context_version_fails_validation() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first)
    assert confirmed is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    result = validate_research_authorization_for_execution(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=2,
    )
    assert result.valid is False
    assert result.reason == "stale_context_version"
    assert (
        get_authorized_research_handoff(
            auth,
            owner=_owner(),
            conversation_id=first.conversation_id,
            decision_id=DECISION_ID,
            canonical_context_version=2,
        )
        is None
    )


def test_client_cannot_widen_frozen_scope() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "Check Amazon too.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    assert first.processing["research_proposal"]["requested_sources"] == ["amazon"]
    confirmed = service.handle(
        {
            "query": "Yes, check Amazon, Shopee and Lazada.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
            "proposal_id": first.processing["proposal_id"],
            "proposal_version": first.processing["proposal_version"],
            "requested_sources": ["amazon", "shopee", "lazada"],
            "expansion_required": True,
            "outside_set_product_names": ["AirPods Max USB-C"],
            "destination_label": "Cebu",
            "requested_evidence_topics": ["warranty"],
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert confirmed is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    assert auth.scope.requested_sources == ("amazon",)
    assert "shopee" not in auth.scope.requested_sources
    assert "lazada" not in auth.scope.requested_sources
    assert auth.scope.outside_set_product_names == ()
    assert auth.scope.expansion_required is False
    assert auth.scope.destination_label is None
    assert (
        list(auth.scope.requested_evidence_topics)
        == first.processing["research_proposal"]["requested_evidence_topics"]
    )
    assert "warranty" not in auth.scope.requested_evidence_topics
    assert auth.scope_digest
    assert auth.scope.requested_sources == tuple(
        first.processing["research_proposal"]["requested_sources"]
    )


def test_cancelled_pending_proposal_cannot_be_authorized() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    cancelled = service.handle(
        {
            "query": "Never mind.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert cancelled is not None
    late = _confirm(service, first)
    assert late is not None
    assert late.processing["answer_status"] == "stale_research_proposal"
    assert "research_authorization_id" not in late.processing
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is None
    assert context.research_authorizations == ()


def test_cancel_after_authorization_blocks_handoff() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first)
    assert confirmed is not None
    cancelled = service.handle(
        {
            "query": "Never mind.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert cancelled is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorizations[0]
    assert auth.status == "cancelled"
    result = validate_research_authorization_for_execution(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
    )
    assert result.valid is False
    assert result.reason == "cancelled"


def test_replacement_after_authorization_invalidates_previous() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    airpods = _confirm(service, first)
    assert airpods is not None
    replaced = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert replaced is not None
    assert replaced.processing["proposal_status"] == "pending_confirmation"
    context = conversations.get(first.conversation_id)
    assert context is not None
    previous = next(
        item
        for item in context.research_authorizations
        if item.authorization_id == airpods.processing["research_authorization_id"]
    )
    assert previous.status == "invalidated"
    assert "AirPods Max" in previous.scope.outside_set_product_names
    result = validate_research_authorization_for_execution(
        previous,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
    )
    assert result.valid is False
    assert result.reason == "invalidated"
    assert context.research_proposal is not None
    assert context.research_proposal.outside_set_product_names == ("Beats Studio Pro",)


def test_destination_authorization_does_not_reprice() -> None:
    service, snapshots, conversations, snapshot = _service()
    before = snapshot.offer_economics
    first = service.handle(
        {"query": "What if I ship it to Cebu?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first, "Go ahead.")
    assert confirmed is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    assert auth.scope.destination_label
    assert "cebu" in auth.scope.destination_label.lower()
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.offer_economics == before
    assert loaded.content_sha256 == snapshot.content_sha256
    assert loaded.recommendation.best_piq_product_id == SONY_ID


def test_session_best_piq_survives_authorization() -> None:
    assistant, snapshots, conversations, _ = _assistant()
    refine = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert refine.processing["session_best_piq_product_id"] == BOSE_ID
    proposed = assistant.query(
        {
            "query": "What about AirPods Max?",
            "decision_id": DECISION_ID,
            "conversation_id": refine.conversation_id,
        },
        owner=_owner(),
    )
    confirmed = assistant.query(
        {
            "query": "Yes, research that",
            "decision_id": DECISION_ID,
            "conversation_id": refine.conversation_id,
            "proposal_id": proposed.processing["proposal_id"],
            "proposal_version": proposed.processing["proposal_version"],
        },
        owner=_owner(),
    )
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert confirmed.processing["session_best_piq_product_id"] == BOSE_ID
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.recommendation.best_piq_product_id == SONY_ID
    context = conversations.get(refine.conversation_id)
    assert context is not None
    assert context.session_refinement is not None
    assert context.session_refinement.session_best_piq_product_id == BOSE_ID
    assert proposed.processing["action"] == "propose_research"


def test_no_pending_proposal_does_not_guess() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "Go ahead.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    assert first.processing["answer_status"] == "no_pending_research_proposal"
    assert "research_authorization_id" not in first.processing
    assert "guess" in first.answer.lower() or "isn't a pending" in first.answer.lower()
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorizations == ()


def test_ambiguous_confirmation_does_not_create_authorization() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    maybe = service.handle(
        {
            "query": "Maybe.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert maybe is not None
    assert maybe.processing["proposal_status"] == "pending_confirmation"
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorizations == ()


def test_handoff_packet_is_bounded_and_non_executing() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first)
    assert confirmed is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    packet = get_authorized_research_handoff(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=context.research_proposal,
    )
    assert packet is not None
    assert packet.execution_available is False
    assert packet.authorization_id == auth.authorization_id
    assert "AirPods Max" in packet.scope.outside_set_product_names
    assert packet.idempotency_key == auth.idempotency_key
    payload = packet.to_dict()
    assert "credential" not in str(payload).lower()
    assert payload["execution_available"] is False
    consumed = mark_research_authorization_consumed(auth, now=START)
    blocked = validate_research_authorization_for_execution(
        consumed,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
    )
    assert blocked.valid is False
    assert blocked.reason == "consumed"


def test_idempotency_key_is_server_derived() -> None:
    owner = _owner()
    first = derive_authorization_idempotency_key(
        owner=owner,
        conversation_id="conv-1",
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal_id="proposal-1",
        proposal_version=1,
        scope_digest="a" * 64,
    )
    second = derive_authorization_idempotency_key(
        owner=owner,
        conversation_id="conv-1",
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal_id="proposal-1",
        proposal_version=1,
        scope_digest="a" * 64,
    )
    other = derive_authorization_idempotency_key(
        owner=owner,
        conversation_id="conv-1",
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal_id="proposal-1",
        proposal_version=2,
        scope_digest="a" * 64,
    )
    assert first == second
    assert first != other
    assert first.startswith("research-auth:")


def test_scope_digest_mismatch_fails_closed() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_research_proposal("Check Amazon too.", packet, snapshot=snapshot)
    assert result is not None and result.proposal is not None
    auth = create_research_authorization_from_proposal(
        replace(result.proposal, conversation_id="conv-scope"),
        owner=_owner(),
        conversation_id="conv-scope",
        now=START,
    )
    widened = replace(result.proposal, requested_sources=("amazon", "shopee", "lazada"))
    checked = validate_research_authorization_for_execution(
        auth,
        owner=_owner(),
        conversation_id="conv-scope",
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=widened,
    )
    assert checked.valid is False
    assert checked.reason == "scope_digest_mismatch"


def test_production_uuid_authorization_does_not_borrow_fixtures() -> None:
    packet = unavailable_packet(DECISION_ID, 1)
    result = compose_research_proposal("What about AirPods Max?", packet)
    assert result is not None and result.proposal is not None
    assert "AirPods Max" in result.proposal.outside_set_product_names
    assert "Sony" not in result.proposal.scope_text
    auth = create_research_authorization_from_proposal(
        replace(result.proposal, conversation_id="conv-uuid"),
        owner=_owner(),
        conversation_id="conv-uuid",
        now=START,
        schema_version="1.2",
    )
    assert "AirPods Max" in auth.scope.outside_set_product_names
    assert auth.evaluated_product_ids == ()


def test_unsupported_schema_fails_closed() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_research_proposal("What about AirPods Max?", packet, snapshot=snapshot)
    assert result is not None and result.proposal is not None
    with pytest.raises(ShoppingAssistantValidationError, match="schema 1.0, 1.1, or 1.2"):
        create_research_authorization_from_proposal(
            replace(result.proposal, conversation_id="conv-schema"),
            owner=_owner(),
            conversation_id="conv-schema",
            now=START,
            schema_version="9.9",
        )


def test_confirmation_matching_helpers() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_research_proposal("What about AirPods Max?", packet, snapshot=snapshot)
    assert result is not None and result.proposal is not None
    proposal = result.proposal
    assert is_explicit_confirmation("Yes, research that.", proposal)
    assert confirmation_correlation("Yes, research that.", proposal) == "missing"
    assert not confirmation_applies_to_proposal("Yes, research that.", proposal)
    assert (
        confirmation_correlation(
            "Yes, research that.",
            proposal,
            client_proposal_id=proposal.proposal_id,
            client_proposal_version=proposal.proposal_version,
        )
        == "match"
    )
    assert confirmation_applies_to_proposal(
        "Yes, research that.",
        proposal,
        client_proposal_id=proposal.proposal_id,
        client_proposal_version=proposal.proposal_version,
    )
    assert confirmation_applies_to_proposal(
        "Yes, research AirPods Max.",
        proposal,
        client_proposal_id=proposal.proposal_id,
        client_proposal_version=proposal.proposal_version,
    )
    assert not confirmation_applies_to_proposal(
        "Yes, research Beats Studio Pro.",
        proposal,
        client_proposal_id=proposal.proposal_id,
        client_proposal_version=proposal.proposal_version,
    )
    assert (
        confirmation_correlation(
            "Yes, research that.",
            proposal,
            client_proposal_id="other-id",
            client_proposal_version=proposal.proposal_version,
        )
        == "stale"
    )
    assert not confirmation_applies_to_proposal(
        "Yes, research that.",
        proposal,
        client_proposal_id="other-id",
        client_proposal_version=proposal.proposal_version,
    )


def test_routing_still_prefers_29_4a_and_29_4b() -> None:
    assistant, _, _, _ = _assistant()
    why = assistant.query(
        {"query": "Why is Sony best?", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert why.processing["action"] == "answer_from_evidence"
    comfort = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert comfort.processing["action"] == "refine_session_recommendation"
    assert comfort.processing["session_best_piq_product_id"] == BOSE_ID


def test_no_network_or_connector_imports() -> None:
    sources = [
        (ROOT / "app/services/research_authorization.py").read_text(encoding="utf-8"),
        (ROOT / "app/domain/entities/research_authorization.py").read_text(encoding="utf-8"),
        (ROOT / "app/services/propose_research.py").read_text(encoding="utf-8"),
    ]
    for source in sources:
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "from requests" not in source
        assert "from httpx" not in source
        assert "urllib.request" not in source
        assert "aiohttp" not in source
        assert "web_search" not in source
        assert "def consume" not in source or "Ask confirmation must not" in source
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "Researching…" not in js
    assert "Researching..." not in js
    assert "propose_research" not in js
    assert "data-proposal-id" in js
    assert "data-proposal-version" in js
    assert "proposal_id" in js
    assert "proposal_version" in js


def test_authorization_creation_does_not_consume() -> None:
    source = (ROOT / "app/services/propose_research.py").read_text(encoding="utf-8")
    assert "mark_research_authorization_consumed" not in source
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    _confirm(service, first)
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_authorization is not None
    assert context.research_authorization.status == "authorized_pending_execution"


def test_evaluated_set_unchanged_after_authorization() -> None:
    service, snapshots, _, snapshot = _service()
    first = service.handle(
        {"query": "Find something cheaper.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first)
    assert confirmed is not None
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.evaluated_product_ids == (SONY_ID, BOSE_ID, SENN_ID)
    assert loaded.recommendation.best_piq_product_id == SONY_ID


@pytest.mark.asyncio
async def test_http_authorization_is_additive_and_non_executing() -> None:
    snapshot = replace(_presentation(), decision_id=AUTH_HTTP_DECISION_ID)
    repo = get_shopping_decision_snapshot_repository()
    repo.add(snapshot)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(OWNER_COOKIE, owner_cookie_payload(_owner()))
        ask = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "What about AirPods Max?",
                "decision_id": AUTH_HTTP_DECISION_ID,
                "surface": "results",
            },
        )
        assert ask.status_code == 200, ask.text
        body = ask.json()
        confirm = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Yes, research that",
                "decision_id": AUTH_HTTP_DECISION_ID,
                "conversation_id": body["conversation_id"],
                "surface": "results",
                "proposal_id": body["research_proposal"]["proposal_id"],
                "proposal_version": body["research_proposal"]["proposal_version"],
                "requested_sources": ["amazon", "shopee"],
            },
        )
        assert confirm.status_code == 200, confirm.text
        payload = confirm.json()
        assert payload["execution_available"] is False
        assert payload["research_handoff_created"] is True
        assert payload["research_handoff_status"] == "authorized_pending_execution"
        assert payload["research_handoff_id"]
        assert "Researching" not in payload["answer"]
        assert payload["processing"]["execution_started"] is False
        repeat = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Yes, research that",
                "decision_id": AUTH_HTTP_DECISION_ID,
                "conversation_id": body["conversation_id"],
                "surface": "results",
                "proposal_id": body["research_proposal"]["proposal_id"],
                "proposal_version": body["research_proposal"]["proposal_version"],
            },
        )
        assert repeat.status_code == 200
        assert repeat.json()["research_handoff_id"] == payload["research_handoff_id"]
        assert repeat.json()["research_handoff_created"] is False
        results = await client.get(f"/results/{AUTH_HTTP_DECISION_ID}")
        assert results.status_code == 200
        assert 'data-best-piq="' + SONY_ID in results.text
        assert "AirPods Max" not in results.text
