"""Sprint 31 research execution router / certified provider contract.

Planning only. No live execution, no canonical mutation, no source-used claims.
"""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerSnapshot,
    CircuitBreakerState,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_authorization import FrozenResearchScope, ResearchAuthorization
from app.domain.entities.research_execution import (
    CapabilityCertification,
    ResearchCapability,
    ResearchProviderDescriptor,
    TrustedMarketContext,
    empty_execution_trace,
)
from app.domain.exceptions import ShoppingAssistantNotFoundError
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.services.research_authorization import (
    cancel_research_authorization,
    derive_authorization_idempotency_key,
    invalidate_research_authorization,
    mark_research_authorization_consumed,
    owner_binding_digest,
    research_scope_digest,
)
from app.services.research_execution import execute_research_plan
from app.services.research_execution_router import plan_authorized_research

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    BOSE_ID,
    DECISION_ID,
    SENN_ID,
    SONY_ID,
    START,
    _owner,
)
from tests.unit.test_phase_29_4c_propose_research import _service
from tests.unit.test_research_authorization_handoff import _confirm

ROOT = Path(__file__).resolve().parents[2]
CONVERSATION_ID = "conversation-sprint-31"
PROPOSAL_ID = "proposal-sprint-31"
AUTH_ID = "authorization-sprint-31"

_DISCOVERY = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
)
_PRICE = (
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
)
_PRICE_SHIP = (
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.SHIPPING,
)


def _scope(**overrides) -> FrozenResearchScope:
    payload = {
        "reason": "outside_evaluated_set",
        "evaluated_product_ids": (SONY_ID, BOSE_ID, SENN_ID),
        "outside_set_product_names": ("AirPods Max",),
    }
    payload.update(overrides)
    return FrozenResearchScope(**payload)


def _authorization(scope: FrozenResearchScope | None = None, **overrides) -> ResearchAuthorization:
    owner = overrides.pop("owner", None) or _owner()
    scope = scope or _scope()
    conversation_id = overrides.get("conversation_id", CONVERSATION_ID)
    decision_id = overrides.get("decision_id", DECISION_ID)
    canonical_context_version = overrides.get("canonical_context_version", 1)
    proposal_id = overrides.get("proposal_id", PROPOSAL_ID)
    proposal_version = overrides.get("proposal_version", 1)
    digest = research_scope_digest(
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal_id=proposal_id,
        proposal_version=proposal_version,
        scope=scope,
    )
    key = derive_authorization_idempotency_key(
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal_id=proposal_id,
        proposal_version=proposal_version,
        scope_digest=digest,
    )
    values = {
        "authorization_id": AUTH_ID,
        "authorization_version": 1,
        "owner_binding": owner_binding_digest(owner),
        "conversation_id": conversation_id,
        "decision_id": decision_id,
        "canonical_context_version": canonical_context_version,
        "proposal_id": proposal_id,
        "proposal_version": proposal_version,
        "scope": scope,
        "scope_digest": digest,
        "proposal_reason": scope.reason,
        "evaluated_product_ids": scope.evaluated_product_ids,
        "idempotency_key": key,
        "status": "authorized_pending_execution",
        "created_at": START,
        "updated_at": START,
        "execution_available": False,
    }
    values.update(overrides)
    values["owner_binding"] = owner_binding_digest(owner)
    return ResearchAuthorization(**values)


def _cert(
    capability: ResearchCapability,
    *,
    markets: tuple[str, ...] = ("PH",),
    sources: tuple[str, ...] = ("amazon",),
    policy: str = "allowed",
    version: str = "cap-v1",
) -> CapabilityCertification:
    return CapabilityCertification(
        capability=capability,
        markets=markets,
        sources=sources,
        policy=policy,
        certification_version=version,
        may_expand_evaluated_set=capability is ResearchCapability.PRODUCT_DISCOVERY,
        can_provide_pricing=capability is ResearchCapability.CURRENT_PRICING,
        can_provide_shipping_taxes=capability
        in {ResearchCapability.SHIPPING, ResearchCapability.TAXES_IMPORT},
        can_provide_product_evidence=capability
        in {
            ResearchCapability.PRODUCT_DISCOVERY,
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.PRODUCT_SPECIFICATION,
            ResearchCapability.WARRANTY_EVIDENCE,
        },
        can_provide_review_evidence=capability is ResearchCapability.REVIEW_COMMUNITY_EVIDENCE,
    )


def _provider(
    provider_id: str = "test-merchant-a",
    *,
    certified: bool = True,
    markets: tuple[str, ...] = ("PH",),
    capabilities: tuple[ResearchCapability, ...] = _DISCOVERY
    + (ResearchCapability.CURRENT_PRICING,),
    sources: tuple[str, ...] = ("amazon",),
    policy: str = "allowed",
    selection_priority: int = 100,
    commission: float | None = None,
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    kill_switch: KillSwitch | None = None,
    circuit: CircuitBreakerSnapshot | None = None,
) -> StaticResearchProvider:
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=provider_id,
            provider_type="test",
            supported_markets=markets,
            supported_capabilities=capabilities,
            supported_sources=sources,
            certification_status="certified" if certified else "registered",
            certification_version="prov-v1",
            operational_status=operational_status,
            capability_certifications=tuple(
                _cert(item, markets=markets, sources=sources, policy=policy) for item in capabilities
            ),
            selection_priority=selection_priority,
            test_fixture=True,
            kill_switch=kill_switch or KillSwitch(),
            circuit_breaker=circuit or CircuitBreakerSnapshot(),
            affiliate_commission_rate=commission,
            may_expand_evaluated_set=ResearchCapability.PRODUCT_DISCOVERY in capabilities,
            can_provide_pricing=ResearchCapability.CURRENT_PRICING in capabilities,
            can_provide_shipping_taxes=ResearchCapability.SHIPPING in capabilities,
            can_provide_product_evidence=True,
        )
    )


def _registry(*providers: StaticResearchProvider):
    return research_provider_registry_for_tests(providers)


def _plan(authorization=None, registry=None, market="PH", **kwargs):
    auth = authorization or _authorization()
    return plan_authorized_research(
        auth,
        owner=kwargs.pop("owner", _owner()),
        conversation_id=kwargs.pop("conversation_id", auth.conversation_id),
        decision_id=kwargs.pop("decision_id", auth.decision_id),
        canonical_context_version=kwargs.pop(
            "canonical_context_version", auth.canonical_context_version
        ),
        registry=registry or _registry(_provider()),
        trusted_market=None if market is None else TrustedMarketContext(country_code=market),
        **kwargs,
    )


def test_valid_authorization_with_certified_provider_is_ready_and_not_executed() -> None:
    result = _plan()
    assert result.planned is True
    plan = result.plan
    assert plan is not None
    assert plan.support_status == "ready"
    assert plan.plan_ready is True
    assert plan.execution_available is False
    assert plan.execution_implemented is False
    assert plan.attempted is False
    assert plan.source_checked is False
    assert plan.eligible_steps
    assert all(not step.attempted for step in plan.eligible_steps)
    assert plan.outside_set_product_names == ("AirPods Max",)
    assert "usb-c" not in " ".join(plan.outside_set_product_names).lower()
    assert "2024" not in " ".join(plan.outside_set_product_names)
    with pytest.raises(NotImplementedError, match="not implemented"):
        execute_research_plan(plan)
    trace = empty_execution_trace(plan.plan_id)
    assert trace.attempted_sources == ()
    assert trace.steps == ()
    public = plan.to_public_dict()
    assert "provider_id" not in public
    assert "plan_digest" not in public
    assert "idempotency" not in str(public).lower()
    assert public["execution_available"] is False
    assert public["source_checked"] is False


def test_uncertified_provider_is_not_eligible() -> None:
    result = _plan(registry=_registry(_provider(certified=False)))
    plan = result.plan
    assert plan is not None
    assert plan.plan_ready is False
    assert plan.eligible_steps == ()
    assert plan.support_status == "blocked_missing_certified_provider"
    assert any(item.reason == "not_certified" for item in plan.blocked_requirements)


def test_wrong_market_does_not_fallback() -> None:
    result = _plan(registry=_registry(_provider(markets=("US",))), market="PH")
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.support_status == "blocked_missing_certified_provider"
    assert any(item.reason == "market_mismatch" for item in plan.blocked_requirements)


def test_source_mismatch_does_not_substitute_shopee_for_amazon() -> None:
    scope = _scope(
        reason="requested_source",
        requested_sources=("amazon",),
        outside_set_product_names=(),
        freshness_required=True,
    )
    result = _plan(
        _authorization(scope),
        registry=_registry(_provider(capabilities=_PRICE, sources=("shopee",))),
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "source_mismatch" for item in plan.blocked_requirements)
    assert "shopee" not in {
        source for step in plan.eligible_steps for source in step.source_identities
    }


def test_capability_mismatch_leaves_requirement_blocked() -> None:
    scope = _scope(
        reason="freshness_required",
        freshness_required=True,
        outside_set_product_names=(),
        requested_sources=("amazon",),
    )
    result = _plan(
        _authorization(scope),
        registry=_registry(
            _provider(capabilities=(ResearchCapability.PRODUCT_SPECIFICATION,), sources=("amazon",))
        ),
    )
    plan = result.plan
    assert plan is not None
    assert ResearchCapability.CURRENT_PRICING in plan.required_capabilities
    assert not any(
        step.capability is ResearchCapability.CURRENT_PRICING for step in plan.eligible_steps
    )
    assert any(
        item.capability is ResearchCapability.CURRENT_PRICING for item in plan.blocked_requirements
    )


def test_multiple_certified_providers_use_deterministic_neutral_selection() -> None:
    high_then_low = _registry(
        _provider("test-zzz-commission", selection_priority=100, commission=0.99),
        _provider("test-aaa-organic", selection_priority=100, commission=0.01),
    )
    low_then_high = _registry(
        _provider("test-zzz-commission", selection_priority=100, commission=0.01),
        _provider("test-aaa-organic", selection_priority=100, commission=0.99),
    )
    first = _plan(registry=high_then_low)
    swapped = _plan(registry=low_then_high)
    second = _plan(registry=high_then_low)
    assert first.plan is not None and swapped.plan is not None and second.plan is not None
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-aaa-organic"}
    assert {step.provider_id for step in swapped.plan.eligible_steps} == {"test-aaa-organic"}
    assert first.plan.plan_digest == second.plan.plan_digest
    assert first.plan.plan_id == second.plan.plan_id
    assert "commission" not in first.plan.to_dict()["eligible_steps"][0]["selection_reason"]
    assert all(
        step.selection_reason == "deterministic_priority_then_provider_id"
        for step in first.plan.eligible_steps
    )


def test_explicit_priority_beats_provider_id_without_using_affiliate() -> None:
    preferred = _provider("test-zzz", selection_priority=1, commission=0.01)
    other = _provider("test-aaa", selection_priority=50, commission=0.99)
    result = _plan(registry=_registry(other, preferred))
    assert result.plan is not None
    assert {step.provider_id for step in result.plan.eligible_steps} == {"test-zzz"}


def test_partial_capabilities_keep_shipping_unknown() -> None:
    scope = _scope(
        reason="freshness_required",
        freshness_required=True,
        requested_evidence_topics=("shipping",),
        requested_sources=("amazon",),
        outside_set_product_names=(),
    )
    result = _plan(
        _authorization(scope),
        registry=_registry(_provider(capabilities=_PRICE, sources=("amazon",))),
    )
    plan = result.plan
    assert plan is not None
    assert plan.support_status == "partially_supported"
    assert plan.plan_ready is False
    assert any(step.capability is ResearchCapability.CURRENT_PRICING for step in plan.eligible_steps)
    shipping = next(
        item for item in plan.blocked_requirements if item.capability is ResearchCapability.SHIPPING
    )
    assert shipping.unknown is True
    assert shipping.fabricated_value is None


def test_production_registry_fail_closes_without_fixture_or_llm_fallback() -> None:
    result = _plan(registry=production_research_provider_registry())
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.support_status == "blocked_missing_certified_provider"
    assert plan.plan_ready is False
    assert plan.execution_available is False
    source = (ROOT / "app/services/research_execution_router.py").read_text(encoding="utf-8")
    assert "openai" not in source.lower()
    assert "web_search" not in source
    assert "FixtureMarketplaceConnector" not in source


def test_stale_cancelled_invalidated_and_consumed_authorizations_are_rejected() -> None:
    cancelled = cancel_research_authorization(_authorization(), now=START)
    invalidated = invalidate_research_authorization(_authorization(), now=START)
    consumed = mark_research_authorization_consumed(_authorization(), now=START)
    for auth, reason in (
        (cancelled, "cancelled"),
        (invalidated, "invalidated"),
        (consumed, "consumed"),
    ):
        result = _plan(auth)
        assert result.planned is False
        assert result.plan is None
        assert result.reason == reason
    stale_context = _authorization(canonical_context_version=2)
    stale = plan_authorized_research(
        stale_context,
        owner=_owner(),
        conversation_id=CONVERSATION_ID,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        registry=_registry(_provider()),
        trusted_market=TrustedMarketContext(country_code="PH"),
    )
    assert stale.planned is False
    assert stale.reason == "stale_context_version"


def test_replaced_authorization_cannot_be_replanned() -> None:
    first = _authorization(proposal_id="proposal-a")
    replaced = invalidate_research_authorization(first, now=START)
    second = _authorization(proposal_id="proposal-b")
    blocked = _plan(replaced)
    allowed = _plan(second)
    assert blocked.planned is False
    assert blocked.reason == "invalidated"
    assert allowed.planned is True


def test_scope_digest_tamper_fail_closes() -> None:
    auth = _authorization()
    result = _plan(auth, expected_scope_digest="0" * 64)
    assert result.planned is False
    assert result.plan is None
    assert result.reason == "scope_digest_mismatch"


def test_idempotent_planning_reuses_logical_plan_identity() -> None:
    registry = _registry(_provider())
    auth = _authorization()
    first = _plan(auth, registry=registry)
    second = _plan(auth, registry=registry)
    assert first.plan is not None and second.plan is not None
    assert first.plan.plan_id == second.plan.plan_id
    assert first.plan.plan_digest == second.plan.plan_digest
    assert first.plan.plan_id != auth.idempotency_key
    assert first.plan.plan_id != auth.authorization_id
    assert first.plan.plan_id.startswith("research-plan:")


def test_planned_provider_does_not_claim_source_used() -> None:
    result = _plan()
    plan = result.plan
    assert plan is not None
    packet = plan.to_dict()
    assert packet["source_checked"] is False
    assert all(step["attempted"] is False for step in packet["eligible_steps"])
    trace = empty_execution_trace(plan.plan_id)
    assert trace.to_dict()["attempted_sources"] == []
    evidence = (ROOT / "app/services/decision_evidence_packet.py").read_text(encoding="utf-8")
    router = (ROOT / "app/services/research_execution_router.py").read_text(encoding="utf-8")
    assert "Source used:" in evidence
    assert "Source used:" not in router
    assert "Amazon was checked" not in router
    assert "I checked Amazon" not in router


def test_outside_product_name_is_not_expanded_to_sku() -> None:
    result = _plan(_authorization(_scope(outside_set_product_names=("AirPods Max",))))
    assert result.plan is not None
    assert result.plan.outside_set_product_names == ("AirPods Max",)


def test_destination_sensitive_scope_is_blocked_without_fake_shipping() -> None:
    scope = _scope(
        reason="reevaluation_required",
        destination_label="Cebu",
        outside_set_product_names=(),
        requested_evidence_topics=("shipping", "import"),
    )
    result = _plan(
        _authorization(scope),
        registry=_registry(
            _provider(
                capabilities=_PRICE_SHIP + (ResearchCapability.TAXES_IMPORT,),
                sources=("amazon",),
            )
        ),
    )
    plan = result.plan
    assert plan is not None
    assert plan.support_status == "blocked_market_context"
    assert plan.plan_ready is False
    assert not any(step.capability is ResearchCapability.SHIPPING for step in plan.eligible_steps)
    assert all(item.fabricated_value is None for item in plan.blocked_requirements)
    assert any(item.reason == "destination_support_not_ready" for item in plan.blocked_requirements)


def test_missing_market_context_is_not_fabricated() -> None:
    result = _plan(market=None)
    plan = result.plan
    assert plan is not None
    assert plan.market is None
    assert plan.support_status == "blocked_market_context"
    assert plan.eligible_steps == ()


def test_wrong_owner_does_not_leak_authorization_existence() -> None:
    auth = _authorization()
    with pytest.raises(ShoppingAssistantNotFoundError):
        plan_authorized_research(
            auth,
            owner=_owner("other-guest"),
            conversation_id=auth.conversation_id,
            decision_id=auth.decision_id,
            canonical_context_version=auth.canonical_context_version,
            registry=_registry(_provider()),
            trusted_market=TrustedMarketContext(country_code="PH"),
        )


def test_client_cannot_select_provider_or_widen_sources() -> None:
    signature = (ROOT / "app/services/research_execution_router.py").read_text(encoding="utf-8")
    start = signature.split("def plan_authorized_research", 1)[1]
    header = start.split(") -> ResearchPlanningResult:", 1)[0]
    assert "provider_id" not in header
    assert "requested_sources" not in header
    scope = _scope(
        requested_sources=("amazon",),
        reason="requested_source",
        outside_set_product_names=(),
    )
    result = _plan(_authorization(scope), registry=_registry(_provider(sources=("amazon",))))
    assert result.plan is not None
    assert result.plan.requested_sources == ("amazon",)


def test_unknown_policy_and_restricted_policy_are_not_executable() -> None:
    unknown = _plan(registry=_registry(_provider(policy="unknown")))
    prohibited = _plan(registry=_registry(_provider(policy="prohibited")))
    restricted = _plan(registry=_registry(_provider(policy="restricted")))
    for result in (unknown, prohibited, restricted):
        assert result.plan is not None
        assert result.plan.eligible_steps == ()
        assert result.plan.plan_ready is False


def test_kill_switch_and_open_circuit_are_ineligible() -> None:
    killed = _plan(registry=_registry(_provider(kill_switch=KillSwitch(engaged=True, reason="off"))))
    open_circuit = _plan(
        registry=_registry(
            _provider(circuit=CircuitBreakerSnapshot(state=CircuitBreakerState.OPEN))
        )
    )
    disabled = _plan(
        registry=_registry(_provider(operational_status=ConnectorOperationalStatus.DISABLED))
    )
    for result in (killed, open_circuit, disabled):
        assert result.plan is not None
        assert result.plan.eligible_steps == ()


def test_generic_cheaper_search_does_not_invent_a_source_preference() -> None:
    scope = _scope(
        reason="evaluated_set_expansion",
        expansion_required=True,
        outside_set_product_names=(),
        requested_sources=(),
    )
    shopee = _provider("test-shopee", sources=("shopee",), selection_priority=10)
    amazon = _provider("test-amazon", sources=("amazon",), selection_priority=20)
    result = _plan(_authorization(scope), registry=_registry(amazon, shopee))
    plan = result.plan
    assert plan is not None
    assert plan.requested_sources == ()
    assert {step.provider_id for step in plan.eligible_steps} == {"test-shopee"}


def test_multi_provider_plan_only_when_capabilities_require_it() -> None:
    scope = _scope(
        reason="insufficient_evidence",
        requested_evidence_topics=("warranty", "review"),
        outside_set_product_names=(),
    )
    manufacturer = _provider(
        "test-manufacturer",
        capabilities=(
            ResearchCapability.WARRANTY_EVIDENCE,
            ResearchCapability.PRODUCT_SPECIFICATION,
        ),
        sources=("manufacturer",),
    )
    community = _provider(
        "test-community",
        capabilities=(ResearchCapability.REVIEW_COMMUNITY_EVIDENCE,),
        sources=("community",),
    )
    result = _plan(_authorization(scope), registry=_registry(manufacturer, community))
    plan = result.plan
    assert plan is not None
    provider_ids = {step.provider_id for step in plan.eligible_steps}
    assert provider_ids == {"test-manufacturer", "test-community"}


def test_authorization_to_plan_does_not_mutate_canonical_decision() -> None:
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
    confirmed = _confirm(service, first)
    assert confirmed is not None
    context = conversations.get(first.conversation_id)
    assert context is not None
    auth = context.research_authorization
    assert auth is not None
    result = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=first.conversation_id,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        registry=_registry(_provider()),
        trusted_market=TrustedMarketContext(country_code="PH"),
    )
    assert result.planned is True
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == before[0]
    assert loaded.canonical_piqscore_set_sha256 == before[1]
    assert loaded.recommendation.snapshot_sha256 == before[2]
    assert loaded.evaluated_product_ids == before[3]
    assert loaded.recommendation.best_piq_product_id == before[4]
    assert loaded.offer_economics == before[5]


def test_router_and_provider_modules_have_no_network_or_live_connectors() -> None:
    files = [
        ROOT / "app/services/research_execution_router.py",
        ROOT / "app/services/research_execution.py",
        ROOT / "app/research/providers.py",
        ROOT / "app/research/registry.py",
        ROOT / "app/research/eligibility.py",
        ROOT / "app/research/capabilities.py",
        ROOT / "app/domain/entities/research_execution.py",
        ROOT / "app/domain/interfaces/research_provider.py",
    ]
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "from requests" not in source
        assert "from httpx" not in source
        assert "urllib.request" not in source
        assert "aiohttp" not in source
        assert "web_search" not in source
        assert "selenium" not in source
        assert "playwright" not in source
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "Researching…" not in js
    assert "Researching..." not in js


def test_public_plan_does_not_expose_certification_secrets_or_commission() -> None:
    result = _plan(registry=_registry(_provider(commission=0.25)))
    public = result.to_public_dict()
    blob = str(public)
    assert "0.25" not in blob
    assert "prov-v1" not in blob
    assert "affiliate" not in blob
    assert "credential" not in blob
    assert result.plan is not None
    assert "affiliate_commission_rate" not in result.plan.to_dict()


def test_planning_does_not_consume_authorization() -> None:
    auth = _authorization()
    result = _plan(auth)
    assert result.planned is True
    assert auth.status == "authorized_pending_execution"


def test_capability_policy_unknown_is_not_enabled_by_payload_presence() -> None:
    descriptor = _provider(policy="unknown").descriptor
    assert descriptor.capability_certifications[0].is_executable is False
    result = _plan(registry=_registry(_provider(policy="unknown")))
    assert result.plan is not None
    assert result.plan.eligible_steps == ()
