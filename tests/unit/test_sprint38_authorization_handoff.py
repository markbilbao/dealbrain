"""Sprint 38 authorization, planning, and execution handoff.

Confirmation stays in the existing ResearchAuthorization chain. Preparation
does not call connectors or consume the authorization.
"""

from __future__ import annotations

import socket
from dataclasses import replace
from datetime import timedelta

import pytest
from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    ResearchCapability,
    TrustedMarketContext,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import ShoppingAssistantNotFoundError
from app.market.support import production_certified_shopping_markets
from app.research.providers import StaticResearchProvider
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.sprint38_live_execution import (
    SHOPPING_RESEARCH_EXECUTION_MODE,
    ExecutionTrace,
    ExecutionTraceStep,
)
from app.services.research_authorization import (
    get_authorized_research_handoff,
    mark_research_authorization_consumed,
)
from app.services.research_execution import (
    AUTHORIZATION_CONSUMPTION_ON_PREPARATION,
    AuthorizedExecutionLedger,
    execute_research_plan,
    prepare_confirmed_research,
    project_to_authoritative_trace,
)
from app.services.research_execution_router import (
    execution_request_from_handoff,
    plan_authorized_research,
)

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    DECISION_ID,
    START,
    _owner,
)
from tests.unit.test_phase_29_4c_propose_research import _service
from tests.unit.test_research_authorization_handoff import _confirm
from tests.unit.test_sprint31_research_execution_router import (
    _authorization,
    _plan,
    _scope,
)


def _prepare_kwargs(auth, ledger, **extra):
    payload = {
        "authorization": auth,
        "owner": extra.pop("owner", _owner()),
        "conversation_id": extra.pop("conversation_id", auth.conversation_id),
        "decision_id": extra.pop("decision_id", auth.decision_id),
        "canonical_context_version": extra.pop(
            "canonical_context_version", auth.canonical_context_version
        ),
        "ledger": ledger,
    }
    payload.update(extra)
    return payload


def test_confirmed_research_prepares_without_a_connector_or_new_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network or connector call")

    execute_calls: list[object] = []

    def _execute(self: StaticResearchProvider, step: object) -> None:
        execute_calls.append(step)
        raise AssertionError("connector execute")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(StaticResearchProvider, "execute", _execute)
    monkeypatch.setattr(
        "app.services.research_authorization.mark_research_authorization_consumed",
        _blocked,
    )

    ledger = AuthorizedExecutionLedger()
    service, snapshots, conversations, snapshot = _service()
    service._execution_ledger = ledger
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
    confirmed = _confirm(service, first)
    assert confirmed is not None
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert confirmed.processing["execution_started"] is False
    assert confirmed.processing["research_executed"] is False
    assert confirmed.processing["source_checked"] is False
    assert confirmed.processing["attempted"] is False
    assert confirmed.processing["execution_available"] is False
    answer = confirmed.answer.casefold()
    assert "approved" in answer
    assert "not available" in answer
    assert "checking now" not in answer
    assert "searched" not in answer
    assert "i found" not in answer
    assert "live result" not in answer
    public = confirmed.processing["research_preparation"]
    blob = str(public).casefold()
    assert "guest-29-4b" not in blob
    assert "session-" not in blob
    assert "scope_digest" not in blob
    assert "idempotency" not in blob
    assert "principal_id" not in blob
    assert public["authorization_consumed"] is False
    assert public["connectors_invoked"] is False
    assert public["live"] is False
    assert public["source_checked"] is False
    assert public["attempted"] is False
    assert public["prior_decision_preserved"] is True

    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorizations[0]
    assert auth.status == "authorized_pending_execution"
    assert auth.idempotency_key.startswith("research-auth:")
    assert AUTHORIZATION_CONSUMPTION_ON_PREPARATION is False
    handoff = get_authorized_research_handoff(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=context.research_proposal,
    )
    assert handoff is not None
    assert handoff.status == "authorized_pending_execution"
    request = execution_request_from_handoff(
        handoff,
        trusted_market=TrustedMarketContext(country_code="PH"),
    )
    assert request.authorization_idempotency_key == auth.idempotency_key
    assert "idempotency_key" not in request.to_dict()
    planned = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=context.research_proposal,
        trusted_market=TrustedMarketContext(country_code="PH"),
        registry=production_research_provider_registry(),
    )
    assert planned.plan is not None
    assert planned.plan.plan_id == public["plan_id"]
    assert planned.plan.source_checked is False
    assert planned.plan.attempted is False
    assert planned.plan.execution_available is False
    assert planned.plan.execution_implemented is False
    assert all(not step.attempted for step in planned.plan.eligible_steps)
    if planned.plan.eligible_steps:
        assert public["outcome"] == "prepared_but_live_unavailable"
        assert "mode_not_live" in public["blocking_reasons"]
    else:
        assert public["outcome"].startswith("blocked_")

    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == before[0]
    assert loaded.canonical_piqscore_set_sha256 == before[1]
    assert loaded.recommendation.snapshot_sha256 == before[2]
    assert loaded.evaluated_product_ids == before[3]
    assert loaded.recommendation.best_piq_product_id == before[4]
    assert loaded.offer_economics == before[5]
    provider = production_research_provider_registry().get("ph-shopify-global-catalog")
    assert provider is not None
    assert provider.descriptor.operational_status.value == "disabled"
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert execute_calls == []
    monkeypatch.undo()
    with pytest.raises(NotImplementedError, match="Sprint 38"):
        provider.execute(None)  # type: ignore[arg-type]


def test_repeated_confirmation_reuses_one_logical_execution() -> None:
    ledger = AuthorizedExecutionLedger()
    service, _, conversations, snapshot = _service()
    service._execution_ledger = ledger
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = _confirm(service, first)
    assert confirmed is not None
    again = _confirm(service, first, query="Yes, research AirPods Max.")
    assert again is not None
    first_id = confirmed.processing["research_preparation"]["execution_id"]
    assert again.processing["research_preparation"]["execution_id"] == first_id
    assert len(ledger) == 1
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert len(context.research_authorizations) == 1
    assert context.research_authorizations[0].status == "authorized_pending_execution"


def test_changed_proposal_scope_and_decision_do_not_reuse_execution() -> None:
    ledger = AuthorizedExecutionLedger()
    service, _, conversations, snapshot = _service()
    service._execution_ledger = ledger
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
    auth = context.research_authorizations[0]
    proposal = context.research_proposal
    assert proposal is not None
    planned = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=proposal,
        trusted_market=TrustedMarketContext(country_code="PH"),
        registry=production_research_provider_registry(),
    )
    assert planned.plan is not None
    version = execute_research_plan(
        planned.plan,
        proposal=replace(proposal, proposal_version=proposal.proposal_version + 1),
        **_prepare_kwargs(auth, ledger),
    )
    assert version.reason == "proposal_version_mismatch"
    assert version.execution_id is None
    assert version.connectors_invoked is False
    scoped = execute_research_plan(
        planned.plan,
        proposal=replace(proposal, requested_sources=("amazon",)),
        **_prepare_kwargs(auth, AuthorizedExecutionLedger()),
    )
    assert scoped.reason == "scope_digest_mismatch"
    assert scoped.execution_id is None
    other = _authorization(decision_id="decision-other", proposal_id="proposal-other")
    other_plan = _plan(other).plan
    assert other_plan is not None
    other_ledger = AuthorizedExecutionLedger()
    prepared_other = execute_research_plan(other_plan, **_prepare_kwargs(other, other_ledger))
    assert prepared_other.execution_id is not None
    original_id = confirmed.processing["research_preparation"]["execution_id"]
    assert prepared_other.execution_id != original_id
    assert len(ledger) == 1


def test_authorization_failures_do_not_start_execution() -> None:
    ledger = AuthorizedExecutionLedger()
    auth = _authorization()
    planned = _plan(auth)
    assert planned.plan is not None
    plan = planned.plan
    missing = execute_research_plan(plan, ledger=ledger)
    assert missing.reason == "not_found"
    assert missing.execution_id is None
    assert missing.connectors_invoked is False
    with pytest.raises(ShoppingAssistantNotFoundError):
        execute_research_plan(plan, **_prepare_kwargs(auth, ledger, owner=_owner("other-shopper")))
    stale_version = auth.canonical_context_version + 1
    stale = execute_research_plan(
        plan,
        **_prepare_kwargs(auth, ledger, canonical_context_version=stale_version),
    )
    assert stale.reason == "stale_context_version"
    assert stale.execution_started is False
    wrong_conversation = execute_research_plan(
        plan,
        **_prepare_kwargs(auth, ledger, conversation_id="conversation-other"),
    )
    assert wrong_conversation.reason == "wrong_conversation"
    cancelled = execute_research_plan(
        plan,
        **_prepare_kwargs(replace(auth, status="cancelled"), ledger),
    )
    assert cancelled.reason == "cancelled"
    invalidated = execute_research_plan(
        plan,
        **_prepare_kwargs(replace(auth, status="invalidated"), ledger),
    )
    assert invalidated.reason == "invalidated"
    consumed_auth = mark_research_authorization_consumed(auth, now=START)
    consumed = execute_research_plan(plan, **_prepare_kwargs(consumed_auth, ledger))
    assert consumed.reason == "consumed"
    assert consumed.execution_id is None
    assert consumed.execution_started is False
    assert len(ledger) == 0
    assert auth.status == "authorized_pending_execution"


def test_same_authorization_reuses_one_binding_and_trace_stays_empty() -> None:
    ledger = AuthorizedExecutionLedger()
    auth = _authorization()
    plan = _plan(auth).plan
    assert plan is not None
    first = execute_research_plan(plan, **_prepare_kwargs(auth, ledger))
    second = execute_research_plan(plan, **_prepare_kwargs(auth, ledger))
    assert first.execution_id == second.execution_id
    assert len(ledger) == 1
    assert first.trace.steps == ()
    assert first.trace.attempted_sources == ()
    assert first.source_checked is False
    assert first.attempted is False
    assert first.live is False
    assert first.shopify_live_call_count == 0
    assert plan.source_checked is False
    assert plan.attempted is False
    assert all(step.attempted is False for step in plan.eligible_steps)
    scripted = ExecutionTrace(
        execution_id="scripted",
        steps=(
            ExecutionTraceStep(
                provider_id="scripted",
                capability=ResearchCapability.CURRENT_PRICING,
                outcome="succeeded",
                attempted=True,
                evaluated_offer_count=1,
                test_fixture=True,
                live=False,
                error_category=None,
                started_at=None,
                finished_at=None,
                attempt_count=1,
            ),
        ),
        started_at=None,
        finished_at=None,
    )
    with pytest.raises(ValueError, match="not production evidence"):
        project_to_authoritative_trace(plan.plan_id, scripted)
    authoritative = project_to_authoritative_trace(plan.plan_id)
    assert authoritative.steps == ()
    assert authoritative.attempted_sources == ()


def test_browser_target_cannot_replace_plan_target() -> None:
    ledger = AuthorizedExecutionLedger()
    auth = _authorization()
    plan = _plan(auth).plan
    assert plan is not None
    assert plan.market is not None
    market = execute_research_plan(
        plan,
        caller_market="US",
        **_prepare_kwargs(auth, ledger),
    )
    assert market.outcome == "caller_target_rejected"
    assert market.reason == "caller_market_rejected"
    assert market.assessed_targets == ()
    assert market.connectors_invoked is False
    capability = execute_research_plan(
        plan,
        caller_capability="shipping",
        **_prepare_kwargs(auth, AuthorizedExecutionLedger()),
    )
    assert capability.reason == "caller_capability_rejected"
    assert capability.assessed_targets == ()
    source = execute_research_plan(
        plan,
        caller_source="shopee",
        **_prepare_kwargs(auth, AuthorizedExecutionLedger()),
    )
    assert source.reason == "caller_source_rejected"
    allowed = execute_research_plan(plan, **_prepare_kwargs(auth, AuthorizedExecutionLedger()))
    assert allowed.outcome == "prepared_but_live_unavailable"
    assert allowed.assessed_targets
    assert {item[0] for item in allowed.assessed_targets} == {plan.market.country_code}
    assert "shipping" not in {item[1] for item in allowed.assessed_targets}
    assert "shopee" not in {item[2] for item in allowed.assessed_targets}
    assert "US" not in {item[0] for item in allowed.assessed_targets}


def test_destination_sensitive_plan_stays_blocked_and_unimplemented() -> None:
    scope = _scope(
        reason="reevaluation_required",
        destination_label="Cebu",
        outside_set_product_names=(),
    )
    auth = _authorization(scope)
    plan = _plan(auth).plan
    assert plan is not None
    assert plan.eligible_steps == ()
    prepared = execute_research_plan(plan, **_prepare_kwargs(auth, AuthorizedExecutionLedger()))
    assert prepared.outcome == "blocked_capability"
    assert "destination_support_not_ready" in prepared.blocking_reasons
    assert prepared.connectors_invoked is False
    assert prepared.attempted is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    direct = prepare_confirmed_research(
        auth,
        owner=_owner(),
        conversation_id=auth.conversation_id,
        decision_id=auth.decision_id,
        canonical_context_version=auth.canonical_context_version,
        ledger=AuthorizedExecutionLedger(),
    )
    assert direct.outcome == "blocked_capability"
    assert direct.connectors_invoked is False
    assert direct.shopify_execute_invoked is False


def test_cancelled_and_invalidated_service_authorizations_do_not_execute() -> None:
    service, _, conversations, snapshot = _service()
    ledger = AuthorizedExecutionLedger()
    service._execution_ledger = ledger
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
    auth = context.research_authorizations[0]
    planned = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        proposal=context.research_proposal,
        trusted_market=TrustedMarketContext(country_code="PH"),
        registry=production_research_provider_registry(),
    )
    assert planned.plan is not None
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
    reloaded = conversations.get(first.conversation_id)
    assert reloaded is not None
    cancelled_auth = reloaded.research_authorizations[0]
    refused = execute_research_plan(
        planned.plan,
        **_prepare_kwargs(cancelled_auth, ledger, conversation_id=first.conversation_id),
    )
    assert refused.reason == "cancelled"
    assert refused.execution_started is False
    assert cancelled_auth.status == "cancelled"


def test_owner_binding_uses_a_different_principal_as_not_found() -> None:
    stranger = ConversationOwner(
        principal_type="guest",
        principal_id="stranger-principal",
        session_id="stranger-session",
        expires_at=START + timedelta(minutes=5),
    )
    auth = _authorization()
    plan = _plan(auth).plan
    with pytest.raises(ShoppingAssistantNotFoundError):
        execute_research_plan(
            plan,
            **_prepare_kwargs(auth, AuthorizedExecutionLedger(), owner=stranger),
        )
