"""Sprint 38 Shopify execution adapter. Fake transport only. No Shopify calls."""

from __future__ import annotations

import io
import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.marketplace_data import SourceMode
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchExecutionTraceStep,
    ResearchProviderDescriptor,
    ResearchProviderStep,
    TrustedMarketContext,
    empty_execution_trace,
)
from app.domain.entities.shopping_assistant import ConversationContext, DecisionContextReference
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.codec import encode_entity
from app.infrastructure.persistence.errors import PersistenceUnavailableError
from app.infrastructure.persistence.session import reset_sync_engine
from app.market.support import production_certified_shopping_markets, shopping_markets_for_tests
from app.marketplace.normalization.shopify_global_catalog import (
    normalize_shopify_global_catalog_offer,
)
from app.research.authorized_execution_repository import (
    EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION,
    AuthorizedExecutionRevisionConflict,
    InMemoryAuthorizedExecutionRepository,
    OperationalAuthorizedExecutionRepository,
)
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    make_research_provider_certification,
)
from app.research.live_start_claim import (
    EXECUTION_CLAIM_LEASE,
    LIVE_CONNECTOR_CLEANUP_MARGIN,
    SHOPIFY_LIVE_HTTP_TIMEOUT,
    InMemoryClaimTransaction,
    LiveStartClaimRequest,
    in_memory_live_start_claims,
    operational_live_start_claims,
    shopify_anonymous_request_contract,
    validate_active_execution_claim,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import ResearchProviderRegistry
from app.research.reliability_repository import (
    InMemoryResearchReliabilityRepository,
    ResearchReliabilityGate,
)
from app.research.reliability_state import BreakerPolicy, advance_recovery, failure_affects_breaker
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    make_research_provider_routing_policy,
    production_research_provider_routing_policy_catalog,
)
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.shopify_global_catalog_certification_evidence import SHOPIFY_GLOBAL_CATALOG_SOURCE
from app.research.shopify_global_catalog_execution import (
    FAKE_TRANSPORT_OBSERVATION_KIND,
    REAL_SHOPIFY_CALLS,
    SHOPIFY_EXECUTION_ADAPTER_IMPLEMENTED,
    SHOPIFY_HTTP_TIMEOUT_SECONDS,
    BoundedFakeTransportPermit,
    ShopifyCatalogAttempt,
    ShopifyCatalogExecutionService,
    execute_production_shopify_catalog,
    in_memory_shopify_execution,
    operational_shopify_execution,
    production_shopify_execution_block_reasons,
)
from app.research.shopify_global_catalog_ph_probe import (
    GLOBAL_CATALOG_ENDPOINT,
    anonymous_http_headers,
)
from app.research.shopify_global_catalog_provider import (
    SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
    shopify_global_catalog_ph_provider,
    shopify_global_catalog_unsupported_capabilities,
)
from app.research.shopify_global_catalog_transport import (
    CatalogTransportResult,
    UrllibJsonTransport,
)
from app.research.sprint38_live_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    SPRINT_38_ENGINEERING_STATUS,
)
from app.services.research_execution_router import plan_authorized_research
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint31_research_execution_router import _authorization, _scope

_DISCOVERY = ResearchCapability.PRODUCT_DISCOVERY
_OFFER = ResearchCapability.OFFER_DISCOVERY
_PRICING = ResearchCapability.CURRENT_PRICING
_AVAILABILITY = ResearchCapability.AVAILABILITY
_MARKET = "PH"
_SOURCE = SHOPIFY_GLOBAL_CATALOG_SOURCE
_NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
_PERMIT = BoundedFakeTransportPermit()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Shopify execution tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(urllib.request, "urlopen", _blocked)


def _token_factory() -> Callable[[], str]:
    counter = {"n": 0}

    def _next() -> str:
        counter["n"] += 1
        return f"opaque-shopify-capability-{counter['n']:04d}"

    return _next


def _provider() -> StaticResearchProvider:
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
            provider_type="merchant",
            supported_markets=(_MARKET,),
            supported_capabilities=SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
            supported_sources=(_SOURCE,),
            operational_status=ConnectorOperationalStatus.AVAILABLE,
            test_fixture=False,
            can_provide_pricing=True,
            can_provide_product_evidence=True,
            may_expand_evaluated_set=True,
        )
    )


def _world():
    provider = _provider()
    records = [
        make_research_provider_certification(
            provider_id=provider.provider_id,
            capability=capability,
            market=_MARKET,
            source=_SOURCE,
            certification_version="shopify-exec-v1",
            test_fixture=False,
        )
        for capability in SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES
    ]
    registry = ResearchProviderRegistry((provider,), allow_test_providers=True)
    catalog = ResearchProviderCertificationCatalog(records, allow_test_certifications=True)
    routing = ResearchProviderRoutingPolicyCatalog(
        (
            make_research_provider_routing_policy(
                provider_id=provider.provider_id,
                routing_priority=1,
                test_fixture=False,
            ),
        ),
        allow_test_policies=True,
    )
    markets = shopping_markets_for_tests((_MARKET,))
    return provider, registry, catalog, routing, markets


def _plan():
    _provider_ignored, registry, catalog, routing, _markets = _world()
    auth = _authorization(
        _scope(
            requested_sources=(_SOURCE,),
            requested_evidence_topics=("availability",),
        )
    )
    planned = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=auth.conversation_id,
        decision_id=auth.decision_id,
        canonical_context_version=auth.canonical_context_version,
        registry=registry,
        catalog=catalog,
        routing_policy=routing,
        trusted_market=TrustedMarketContext(country_code=_MARKET),
    )
    assert planned.plan is not None
    return auth, planned.plan, registry, catalog, routing, _markets


def _seed(conversations, auth) -> ConversationContext:
    context = ConversationContext(
        conversation_id=auth.conversation_id,
        turns=(),
        expires_at=datetime(2030, 6, 1, tzinfo=UTC),
        owner=_owner(),
        decision_context=DecisionContextReference(
            decision_id=auth.decision_id,
            context_version=auth.canonical_context_version,
            evaluated_product_ids=auth.evaluated_product_ids,
            canonical_piqscore_snapshot_sha256="ab" * 32,
            recommendation_snapshot_sha256="cd" * 32,
        ),
        research_authorizations=(auth,),
    )
    return conversations.save(context)


def _claim_request(auth, plan, registry, catalog, routing, markets, *, now: datetime, capability):
    return LiveStartClaimRequest(
        authorization=auth,
        owner=_owner(),
        plan=plan,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        market=_MARKET,
        capability=capability,
        source=_SOURCE,
        now=now,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        registry=registry,
        certifications=catalog,
        routing=routing,
        certified_markets=markets,
        mode="live",
    )


class FakeCatalogTransport:
    def __init__(
        self,
        result: CatalogTransportResult | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def post_json(self, endpoint, headers, payload, timeout_seconds):
        self.calls.append(
            {
                "endpoint": endpoint,
                "headers": dict(headers),
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class _OutcomeCasFailure(InMemoryClaimTransaction):
    def __init__(self, *args, error: Exception, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._error = error

    def cas_execution(self, record, *, expected_revision: int):
        if record.state in {"completed", "failed", "outcome_unknown"}:
            raise self._error
        return super().cas_execution(record, expected_revision=expected_revision)


def _service_with(
    executions,
    reliability,
    conversations,
    transport,
    *,
    error: Exception | None = None,
    clock: Callable[[], datetime] | None = None,
):
    if error is None:
        return in_memory_shopify_execution(
            executions,
            reliability,
            conversations,
            transport,
            clock=clock,
        )

    def factory():
        return _OutcomeCasFailure(executions, reliability, conversations, error=error)

    return ShopifyCatalogExecutionService(factory, transport, clock=clock)


def _product(
    *,
    currency: str = "USD",
    amount: int | None = 79900,
    seller: str = "North Audio",
) -> dict:
    variant: dict[str, Any] = {
        "id": "variant-north-1",
        "title": "256GB",
        "checkout_url": "https://north-audio.merchant.test/cart/1",
        "availability": {"available": True, "status": "in_stock"},
        "seller": {
            "name": seller,
            "id": "shop-north",
            "domain": "north-audio.merchant.test",
            "url": "https://north-audio.merchant.test",
        },
    }
    if amount is not None:
        variant["price"] = {"amount": amount, "currency": currency}
    return {
        "id": "gid://shopify/Product/earbuds-1",
        "title": "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "url": "https://north-audio.merchant.test/products/item",
        "variants": [variant],
    }


def _envelope(product: dict, *, single: bool = False) -> dict:
    content = {"product": product} if single else {"products": [product]}
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"isError": False, "structuredContent": content},
    }


def _ok(product: dict, *, single: bool = False) -> CatalogTransportResult:
    return CatalogTransportResult(status_code=200, payload=_envelope(product, single=single))


def _step(plan, capability: ResearchCapability) -> ResearchProviderStep:
    return next(step for step in plan.eligible_steps if step.capability is capability)


def _prepare(*, now: datetime = _NOW, half_open: bool = False, capability: ResearchCapability):
    auth, plan, registry, catalog, routing, markets = _plan()
    executions = InMemoryAuthorizedExecutionRepository()
    reliability = InMemoryResearchReliabilityRepository()
    executions.bind(
        authorization_idempotency_key=auth.idempotency_key,
        authorization_id=auth.authorization_id,
        authorization_version=auth.authorization_version,
        decision_id=auth.decision_id,
        plan_id=plan.plan_id,
        now=now,
    )
    if half_open:
        gate = ResearchReliabilityGate(
            reliability,
            policy=BreakerPolicy(failure_threshold=1, recovery_window_ms=1_000),
        )
        opened = gate.record_failure(
            SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
            _MARKET,
            ConnectorFailureKind.TIMEOUT,
            now=now - timedelta(seconds=2),
        )
        advanced = advance_recovery(opened, now=now)
        reliability.save(advanced, expected_revision=opened.revision)
    service, _executions, _reliability = in_memory_live_start_claims(
        executions,
        reliability,
        token_factory=_token_factory(),
    )
    assert service.conversations is not None
    seeded = _seed(service.conversations, auth)
    claim = service.claim(
        _claim_request(
            auth,
            plan,
            registry,
            catalog,
            routing,
            markets,
            now=now,
            capability=capability,
        )
    )
    assert claim.claimed is True
    assert claim.claim_capability is not None
    return {
        "auth": auth,
        "plan": plan,
        "executions": executions,
        "reliability": reliability,
        "conversations": service.conversations,
        "claim": claim,
        "decision": seeded.decision_context,
        "registry": registry,
        "catalog": catalog,
        "routing": routing,
        "markets": markets,
    }


def _attempt(
    prepared,
    *,
    capability: ResearchCapability,
    operation: str,
    **kwargs,
):
    values = {
        "permit": _PERMIT,
        "authorization": prepared["auth"],
        "owner": _owner(),
        "plan": prepared["plan"],
        "step": _step(prepared["plan"], capability),
        "source": _SOURCE,
        "operation": operation,
        "claim_capability": prepared["claim"].claim_capability,
        "probe_capability": prepared["claim"].probe_capability,
        "harness_operational_status": ConnectorOperationalStatus.AVAILABLE,
        "catalog_query": "wireless earbuds" if operation == "search_catalog" else None,
        "product_id": "gid://shopify/Product/earbuds-1" if operation == "get_product" else None,
    }
    values.update(kwargs)
    return ShopifyCatalogAttempt(**values)


def _frozen_clock(moment: datetime) -> Callable[[], datetime]:
    def _clock() -> datetime:
        return moment

    return _clock


def _clock_sequence(*moments: datetime) -> Callable[[], datetime]:
    pending = list(moments)

    def _clock() -> datetime:
        if len(pending) > 1:
            return pending.pop(0)
        return pending[0]

    return _clock


def _run(
    prepared,
    transport: FakeCatalogTransport,
    attempt: ShopifyCatalogAttempt,
    *,
    error=None,
    at: datetime = _NOW,
    clock: Callable[[], datetime] | None = None,
):
    service = _service_with(
        prepared["executions"],
        prepared["reliability"],
        prepared["conversations"],
        transport,
        error=error,
        clock=clock or _frozen_clock(at),
    )
    return service.execute(attempt)


def _assert_contract(call: Mapping[str, Any], *, tool: str) -> None:
    assert call["endpoint"] == GLOBAL_CATALOG_ENDPOINT
    assert call["timeout_seconds"] == 5.0
    assert call["timeout_seconds"] == SHOPIFY_HTTP_TIMEOUT_SECONDS
    headers = call["headers"]
    assert headers == anonymous_http_headers()
    assert "Authorization" not in headers
    assert "Signature" not in headers
    assert "X-Signature" not in headers
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"]
    payload = call["payload"]
    assert payload["method"] == "tools/call"
    assert payload["params"]["name"] == tool
    assert payload["params"]["name"] != "lookup_catalog"
    catalog = payload["params"]["arguments"]["catalog"]
    assert catalog["context"]["address_country"] == "PH"
    assert catalog["context"]["currency"] == "PHP"
    assert catalog["filters"]["ships_to"] == {"country": "PH"}
    assert "ids" not in catalog
    pagination = catalog.get("pagination")
    if tool == "search_catalog":
        assert catalog["view"] == "offer"
        assert pagination == {"limit": 10}
        assert "cursor" not in pagination
    else:
        assert pagination is None
        assert "," not in catalog["id"]


def _encoded(record) -> str:
    return json.dumps(encode_entity(record))


def test_fake_search_catalog_success_records_trace_and_releases_claim() -> None:
    prepared = _prepare(capability=_DISCOVERY)
    transport = FakeCatalogTransport(_ok(_product(currency="USD")))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_DISCOVERY, operation="search_catalog"),
    )
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    assert result.durable_success is True
    assert result.attempted is True
    assert result.transport_invoked is True
    assert result.persisted is True
    assert result.state == "completed"
    assert result.outcome == "succeeded"
    assert result.evaluated_offer_count == 1
    assert result.normalized_offer_count == 1
    assert result.returned_currencies == ("USD",)
    assert result.observation_kind == FAKE_TRANSPORT_OBSERVATION_KIND
    assert result.observation_kind != "live"
    assert result.source_mode_live is False
    assert result.raw_response_persisted is False
    assert result.real_shopify_call_count == 0
    assert result.retry_count == 0
    assert result.claim_released is True
    assert result.unknown_cost_components == ("shipping", "tax", "import", "voucher")
    assert result.live_research_execution_operational is False
    assert result.trace is not None
    assert result.trace.attempted_sources == (_SOURCE,)
    assert result.trace.succeeded_sources == (_SOURCE,)
    assert result.trace.failed_sources == ()
    assert result.trace.timed_out_sources == ()
    assert result.trace.evaluated_offer_count == 1
    assert result.trace.steps[0].freshness_checked_at is None
    assert result.trace.steps[0].attempt_status == "succeeded"
    assert result.trace.steps[0].evidence_ids == ()
    assert result.trace.steps[0].evaluated_offer_count == 1
    assert len(transport.calls) == 1
    _assert_contract(transport.calls[0], tool="search_catalog")
    assert stored is not None
    assert stored.state == "completed"
    assert stored.claim_digest is None
    assert stored.raw_response_persisted is False
    assert stored.observation_kind == "synthetic"
    assert stored.normalized_amount_minors == (79900,)
    assert stored.trace is not None
    assert stored.evidence_ids == ()
    assert len(stored.normalized_offer_digests) == 1
    assert stored.normalized_offer_digests[0] not in stored.trace.steps[0].evidence_ids
    assert "Apple" not in stored.normalized_offer_digests[0]
    encoded = _encoded(stored)
    assert "jsonrpc" not in encoded
    assert "structuredContent" not in encoded
    assert "checkout_url" not in encoded
    assert "Apple iPhone 17 Pro Max" not in encoded
    assert prepared["claim"].claim_capability not in encoded
    assert (
        validate_active_execution_claim(
            stored,
            claim_capability=prepared["claim"].claim_capability or "",
            now=_NOW,
        ).valid
        is False
    )
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert breaker.state is CircuitBreakerState.CLOSED
    assert breaker.consecutive_failure_count == 0
    assert breaker.last_success_at == _NOW
    assert breaker.half_open_probe_claim_digest is None
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert SHOPIFY_LIVE_CALL_PERMITTED is False


def test_fake_get_product_success_preserves_source_currency() -> None:
    prepared = _prepare(capability=_PRICING)
    transport = FakeCatalogTransport(_ok(_product(currency="EUR"), single=True))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_PRICING, operation="get_product"),
    )
    assert result.durable_success is True
    assert result.returned_currencies == ("EUR",)
    assert result.observation_kind == "synthetic"
    assert result.source_mode_live is False
    assert len(transport.calls) == 1
    _assert_contract(transport.calls[0], tool="get_product")
    assert transport.calls[0]["payload"]["params"]["name"] != "lookup_catalog"
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    assert stored is not None
    assert stored.trace is not None
    assert stored.trace.succeeded_sources == (_SOURCE,)
    assert stored.normalized_amount_minors == (79900,)
    assert SourceMode.LIVE.value not in _encoded(stored)


def test_lookup_catalog_and_unsupported_capability_block_before_transport() -> None:
    prepared = _prepare(capability=_OFFER)
    lookup = FakeCatalogTransport(_ok(_product()))
    refused = _run(
        prepared,
        lookup,
        _attempt(
            prepared,
            capability=_OFFER,
            operation="lookup_catalog",
            catalog_query="wireless earbuds",
            product_id=None,
        ),
    )
    assert refused.block_reason == "catalog_tool_forbidden"
    assert lookup.calls == []
    assert prepared["executions"].get(prepared["claim"].execution_id or "").state == (  # type: ignore[union-attr]
        "claimed_for_attempt"
    )
    shipping = FakeCatalogTransport(_ok(_product()))
    forged = ResearchProviderStep(
        step_index=1,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        provider_type="merchant",
        capability=ResearchCapability.SHIPPING,
        source_identities=(_SOURCE,),
        market=_MARKET,
        certification_id="forged",
        certification_version="v1",
        selection_reason="unsupported",
    )
    blocked = _run(
        prepared,
        shipping,
        _attempt(
            prepared,
            capability=_OFFER,
            operation="search_catalog",
            step=forged,
        ),
    )
    assert blocked.block_reason == "capability_not_supported"
    assert shipping.calls == []
    for capability in shopify_global_catalog_unsupported_capabilities():
        assert capability not in SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES


def test_claim_identity_expiry_and_budget_block_before_transport() -> None:
    missing = _prepare(capability=_AVAILABILITY)
    unclaimed = missing["executions"].get(missing["claim"].execution_id or "")
    assert unclaimed is not None
    missing["executions"].cas_replace(
        replace(
            unclaimed,
            state="prepared_unavailable",
            claimed_at=None,
            claim_expires_at=None,
            claim_digest=None,
        ),
        expected_revision=unclaimed.revision,
    )
    transport = FakeCatalogTransport(_ok(_product()))
    no_claim = _run(
        missing,
        transport,
        _attempt(missing, capability=_AVAILABILITY, operation="search_catalog"),
    )
    assert no_claim.block_reason == "execution_not_claimed"
    assert transport.calls == []

    expired = _prepare(capability=_AVAILABILITY)
    late = FakeCatalogTransport(_ok(_product()))
    expired_result = _run(
        expired,
        late,
        _attempt(expired, capability=_AVAILABILITY, operation="search_catalog"),
        at=_NOW + EXECUTION_CLAIM_LEASE,
    )
    assert expired_result.block_reason == "execution_claim_expired"
    assert late.calls == []

    wrong = _prepare(capability=_AVAILABILITY)
    mismatch = FakeCatalogTransport(_ok(_product()))
    wrong_result = _run(
        wrong,
        mismatch,
        _attempt(
            wrong,
            capability=_AVAILABILITY,
            operation="search_catalog",
            claim_capability="not-the-active-claim-capability",
        ),
    )
    assert wrong_result.block_reason == "execution_claim_identity_mismatch"
    assert mismatch.calls == []

    budget = _prepare(capability=_AVAILABILITY)
    short = FakeCatalogTransport(_ok(_product()))
    remaining = SHOPIFY_LIVE_HTTP_TIMEOUT + LIVE_CONNECTOR_CLEANUP_MARGIN - timedelta(seconds=1)
    budget_result = _run(
        budget,
        short,
        _attempt(budget, capability=_AVAILABILITY, operation="search_catalog"),
        at=_NOW + EXECUTION_CLAIM_LEASE - remaining,
    )
    assert budget_result.block_reason == "claim_budget_insufficient"
    assert short.calls == []
    assert budget["executions"].get(budget["claim"].execution_id or "").state == (  # type: ignore[union-attr]
        "claimed_for_attempt"
    )


def test_crash_before_http_can_reclaim_the_same_execution() -> None:
    prepared = _prepare(capability=_DISCOVERY)
    transport = FakeCatalogTransport(_ok(_product()))
    too_late = _NOW + EXECUTION_CLAIM_LEASE - timedelta(seconds=5)
    refused = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_DISCOVERY, operation="search_catalog"),
        at=too_late,
    )
    assert refused.block_reason == "claim_budget_insufficient"
    assert transport.calls == []

    def _reclaim_tokens() -> Callable[[], str]:
        return lambda: "reclaimed-shopify-capability-0002"

    service, _executions, _reliability = in_memory_live_start_claims(
        prepared["executions"],
        prepared["reliability"],
        prepared["conversations"],
        token_factory=_reclaim_tokens(),
    )
    reclaimed = service.claim(
        _claim_request(
            prepared["auth"],
            prepared["plan"],
            prepared["registry"],
            prepared["catalog"],
            prepared["routing"],
            prepared["markets"],
            now=_NOW + EXECUTION_CLAIM_LEASE,
            capability=_DISCOVERY,
        )
    )
    assert reclaimed.claimed is True
    assert reclaimed.claim_capability != prepared["claim"].claim_capability
    assert transport.calls == []
    stored = prepared["executions"].get(reclaimed.execution_id or "")
    assert stored is not None
    assert stored.state == "claimed_for_attempt"


def test_half_open_probe_must_be_active_before_transport() -> None:
    prepared = _prepare(capability=_OFFER, half_open=True)
    assert prepared["claim"].probe_capability is not None
    missing = FakeCatalogTransport(_ok(_product()))
    no_probe = _run(
        prepared,
        missing,
        _attempt(
            prepared,
            capability=_OFFER,
            operation="search_catalog",
            probe_capability=None,
        ),
    )
    assert no_probe.block_reason == "half_open_probe_not_active"
    assert missing.calls == []

    wrong = FakeCatalogTransport(_ok(_product()))
    mismatched = _run(
        prepared,
        wrong,
        _attempt(
            prepared,
            capability=_OFFER,
            operation="search_catalog",
            probe_capability="wrong-probe-capability-value",
        ),
    )
    assert mismatched.block_reason == "half_open_probe_identity_mismatch"
    assert wrong.calls == []

    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    shortened = prepared["reliability"].save(
        replace(breaker, half_open_probe_expires_at=_NOW + timedelta(seconds=5)),
        expected_revision=breaker.revision,
    )
    expired = FakeCatalogTransport(_ok(_product()))
    expired_result = _run(
        prepared,
        expired,
        _attempt(prepared, capability=_OFFER, operation="search_catalog"),
        at=shortened.half_open_probe_expires_at or _NOW,
    )
    assert expired_result.block_reason == "half_open_probe_expired"
    assert expired.calls == []
    assert prepared["executions"].get(prepared["claim"].execution_id or "").state == (  # type: ignore[union-attr]
        "claimed_for_attempt"
    )


def test_production_composition_cannot_reach_transport() -> None:
    transport = FakeCatalogTransport(_ok(_product()))
    result = execute_production_shopify_catalog(transport)
    assert transport.calls == []
    assert result.transport_invoked is False
    assert result.attempted is False
    assert result.persisted is False
    assert result.real_shopify_call_count == 0
    reasons = production_shopify_execution_block_reasons()
    assert "mode_not_live" in reasons
    assert "shopify_live_call_not_permitted" in reasons
    assert "production_ucp_profile_undeployed" in reasons
    assert "market_not_eligible" in reasons
    assert "routing_absent" in reasons
    assert result.block_reason == reasons[0]
    provider = shopify_global_catalog_ph_provider()
    assert provider.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    with pytest.raises(NotImplementedError):
        provider.execute(_step_unused())
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SPRINT_41_STATUS == "UNSTARTED"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert SHOPIFY_EXECUTION_ADAPTER_IMPLEMENTED is True
    assert REAL_SHOPIFY_CALLS == 0
    assert EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION is False
    contract = shopify_anonymous_request_contract()
    assert contract.http_implemented is False
    assert empty_execution_trace("plan-not-attempted").attempted_sources == ()


def _step_unused() -> ResearchProviderStep:
    return ResearchProviderStep(
        step_index=1,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        provider_type="merchant",
        capability=_PRICING,
        source_identities=(_SOURCE,),
        market=_MARKET,
        certification_id="unused",
        certification_version="v1",
        selection_reason="production execute stays unimplemented",
    )


def test_disabled_harness_status_blocks_before_transport() -> None:
    prepared = _prepare(capability=_PRICING)
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        prepared,
        transport,
        _attempt(
            prepared,
            capability=_PRICING,
            operation="get_product",
            harness_operational_status=ConnectorOperationalStatus.DISABLED,
        ),
    )
    assert result.block_reason == "provider_disabled"
    assert transport.calls == []


@pytest.mark.parametrize(
    ("result", "reason", "kind", "status", "affects"),
    [
        (
            CatalogTransportResult(status_code=0, payload=None, timed_out=True),
            "timeout",
            ConnectorFailureKind.TIMEOUT,
            "timed_out",
            True,
        ),
        (
            CatalogTransportResult(status_code=429, payload={"error": "slow down"}),
            "rate_limit",
            ConnectorFailureKind.RATE_LIMIT,
            "failed",
            False,
        ),
        (
            CatalogTransportResult(status_code=401, payload={"error": "unauthorized"}),
            "credential",
            ConnectorFailureKind.CREDENTIAL,
            "failed",
            False,
        ),
        (
            CatalogTransportResult(status_code=503, payload={"error": "down"}),
            "unavailable",
            ConnectorFailureKind.UNAVAILABLE,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=429, payload=None, malformed=True),
            "rate_limit",
            ConnectorFailureKind.RATE_LIMIT,
            "failed",
            False,
        ),
        (
            CatalogTransportResult(status_code=503, payload=None, malformed=True),
            "unavailable",
            ConnectorFailureKind.UNAVAILABLE,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=401, payload=None, malformed=True),
            "credential",
            ConnectorFailureKind.CREDENTIAL,
            "failed",
            False,
        ),
        (
            CatalogTransportResult(status_code=403, payload=None, malformed=True),
            "credential",
            ConnectorFailureKind.CREDENTIAL,
            "failed",
            False,
        ),
        (
            CatalogTransportResult(status_code=200, payload=None, malformed=True),
            "malformed_jsonrpc",
            ConnectorFailureKind.UNKNOWN,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=200, payload={"jsonrpc": "2.0"}),
            "malformed_jsonrpc",
            ConnectorFailureKind.UNKNOWN,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=404, payload=None, malformed=True),
            "http_error",
            ConnectorFailureKind.UNKNOWN,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=0, payload=None, transport_unavailable=True),
            "unavailable",
            ConnectorFailureKind.UNAVAILABLE,
            "failed",
            True,
        ),
        (
            CatalogTransportResult(status_code=200, payload=_envelope(_product(amount=None))),
            "missing_price",
            ConnectorFailureKind.PARTIAL,
            "failed",
            False,
        ),
    ],
)
def test_failure_traces_and_breaker_policy(result, reason, kind, status, affects) -> None:
    prepared = _prepare(capability=_PRICING)
    transport = FakeCatalogTransport(result)
    outcome = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_PRICING, operation="get_product"),
    )
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    assert outcome.durable_success is False
    assert outcome.persisted is True
    assert outcome.state == "failed"
    assert outcome.outcome == status
    assert outcome.error_category == reason
    assert outcome.failure_kind == kind.value
    assert outcome.evaluated_offer_count == 0
    assert outcome.observation_kind == "synthetic"
    assert outcome.claim_released is True
    assert len(transport.calls) == 1
    assert stored is not None
    assert stored.trace is not None
    assert stored.trace.attempted_sources == (_SOURCE,)
    assert stored.trace.steps[0].attempt_status == status
    assert stored.trace.steps[0].error_category == reason
    assert stored.trace.steps[0].freshness_checked_at is None
    assert stored.raw_response_persisted is False
    assert "jsonrpc" not in _encoded(stored) or reason == "malformed_jsonrpc"
    if reason == "malformed_jsonrpc":
        assert "structuredContent" not in _encoded(stored)
    if status == "timed_out":
        assert stored.trace.timed_out_sources == (_SOURCE,)
        assert stored.trace.failed_sources == ()
    else:
        assert stored.trace.failed_sources == (_SOURCE,)
        assert stored.trace.timed_out_sources == ()
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert breaker.last_failure_category is kind
    assert breaker.last_success_at is None
    assert failure_affects_breaker(kind) is affects
    if affects:
        assert breaker.consecutive_failure_count == 1
    else:
        assert breaker.consecutive_failure_count == 0
        assert breaker.state is CircuitBreakerState.CLOSED


def test_half_open_success_closes_breaker_and_failure_reopens_it() -> None:
    success = _prepare(capability=_DISCOVERY, half_open=True)
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        success,
        transport,
        _attempt(success, capability=_DISCOVERY, operation="search_catalog"),
    )
    assert result.durable_success is True
    closed = success["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert closed.state is CircuitBreakerState.CLOSED
    assert closed.consecutive_failure_count == 0
    assert closed.last_success_at == _NOW
    assert closed.half_open_probe_claim_digest is None

    failure = _prepare(capability=_DISCOVERY, half_open=True)
    failed_transport = FakeCatalogTransport(
        CatalogTransportResult(status_code=0, payload=None, timed_out=True)
    )
    failed = _run(
        failure,
        failed_transport,
        _attempt(failure, capability=_DISCOVERY, operation="search_catalog"),
    )
    assert failed.persisted is True
    assert failed.outcome == "timed_out"
    opened = failure["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert opened.state is CircuitBreakerState.OPEN
    assert opened.half_open_probe_claim_digest is None
    assert opened.last_success_at is None


def test_terminal_execution_cannot_be_resumed_or_overwritten() -> None:
    prepared = _prepare(capability=_OFFER)
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_OFFER, operation="search_catalog"),
    )
    assert result.durable_success is True
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    assert stored is not None
    service, _executions, _reliability = in_memory_live_start_claims(
        prepared["executions"],
        prepared["reliability"],
        prepared["conversations"],
        token_factory=_token_factory(),
    )
    again = service.claim(
        _claim_request(
            prepared["auth"],
            prepared["plan"],
            prepared["registry"],
            prepared["catalog"],
            prepared["routing"],
            prepared["markets"],
            now=_NOW,
            capability=_OFFER,
        )
    )
    assert again.claimed is False
    assert again.block_reason == "execution_terminal"
    second = FakeCatalogTransport(_ok(_product(currency="GBP")))
    repeated = _run(
        prepared,
        second,
        _attempt(prepared, capability=_OFFER, operation="search_catalog"),
    )
    assert repeated.block_reason == "execution_terminal"
    assert second.calls == []
    current = prepared["executions"].get(stored.execution_id)
    assert current is not None
    assert current.revision == stored.revision
    assert current.returned_currencies == ("USD",)
    with pytest.raises(AuthorizedExecutionRevisionConflict):
        prepared["executions"].cas_replace(current, expected_revision=current.revision - 1)
    unchanged = prepared["executions"].get(stored.execution_id)
    assert unchanged is not None
    assert unchanged.outcome == "succeeded"
    assert unchanged.returned_currencies == ("USD",)
    decision = prepared["conversations"].get(prepared["auth"].conversation_id)
    assert decision is not None
    assert decision.decision_context == prepared["decision"]


def test_stale_or_failed_outcome_write_does_not_fabricate_success() -> None:
    stale = _prepare(capability=_PRICING)
    stale_transport = FakeCatalogTransport(_ok(_product()))
    stale_result = _run(
        stale,
        stale_transport,
        _attempt(stale, capability=_PRICING, operation="get_product"),
        error=AuthorizedExecutionRevisionConflict("research-exec:stale", 1),
    )
    assert len(stale_transport.calls) == 1
    assert stale_result.persisted is False
    assert stale_result.durable_success is False
    assert stale_result.block_reason == "stale_outcome_rejected"
    running = stale["executions"].get(stale["claim"].execution_id or "")
    assert running is not None
    assert running.state == "running"
    assert running.outcome is None
    breaker = stale["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert breaker.last_success_at is None

    failed = _prepare(capability=_PRICING)
    failed_transport = FakeCatalogTransport(_ok(_product()))
    failed_result = _run(
        failed,
        failed_transport,
        _attempt(failed, capability=_PRICING, operation="get_product"),
        error=PersistenceUnavailableError("outcome store unavailable"),
    )
    assert len(failed_transport.calls) == 1
    assert failed_result.persisted is False
    assert failed_result.durable_success is False
    assert failed_result.block_reason == "outcome_persistence_unavailable"
    assert failed_result.outcome is None
    left = failed["executions"].get(failed["claim"].execution_id or "")
    assert left is not None
    assert left.state == "running"
    assert left.trace is None
    untouched = failed["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    assert untouched.last_success_at is None
    assert untouched.consecutive_failure_count == 0


def test_ambiguous_post_http_crash_does_not_replay_or_close_breaker() -> None:
    prepared = _prepare(capability=_DISCOVERY, half_open=True)
    transport = FakeCatalogTransport(error=RuntimeError("worker lost the response"))
    attempt = _attempt(
        prepared,
        capability=_DISCOVERY,
        operation="search_catalog",
    )
    ambiguous = _run(prepared, transport, attempt)
    assert len(transport.calls) == 1
    assert ambiguous.transport_outcome_ambiguous is True
    assert ambiguous.persisted is False
    assert ambiguous.durable_success is False
    assert ambiguous.block_reason == "ambiguous_transport_outcome"
    running = prepared["executions"].get(prepared["claim"].execution_id or "")
    assert running is not None
    assert running.state == "running"
    moments = [_NOW, _NOW + timedelta(seconds=1)]

    def _reconcile_clock() -> datetime:
        return moments.pop(0)

    service = in_memory_shopify_execution(
        prepared["executions"],
        prepared["reliability"],
        prepared["conversations"],
        transport,
        clock=_reconcile_clock,
    )
    still_claimed = service.reconcile_ambiguous(attempt)
    assert still_claimed.block_reason == "attempt_still_claimed"
    assert len(transport.calls) == 1
    expired = replace(running, claim_expires_at=_NOW + timedelta(seconds=1))
    prepared["executions"].cas_replace(expired, expected_revision=running.revision)
    reconciled = service.reconcile_ambiguous(
        _attempt(prepared, capability=_DISCOVERY, operation="search_catalog")
    )
    assert reconciled.persisted is True
    assert reconciled.state == "outcome_unknown"
    assert reconciled.outcome == "outcome_unknown"
    assert reconciled.transport_invoked is False
    assert reconciled.durable_success is False
    assert len(transport.calls) == 1
    stored = prepared["executions"].get(running.execution_id)
    assert stored is not None
    assert stored.claim_digest is None
    assert stored.trace is not None
    assert stored.trace.steps[0].attempt_status == "outcome_unknown"
    assert stored.trace.succeeded_sources == ()
    assert stored.trace.failed_sources == ()
    assert stored.trace.timed_out_sources == ()
    assert stored.evaluated_offer_count == 0
    assert stored.finished_at == _NOW + timedelta(seconds=1)
    assert stored.evidence_ids == ()
    assert stored.normalized_offer_digests == ()
    assert stored.trace.steps[0].finished_at == _NOW + timedelta(seconds=1)
    assert stored.trace.steps[0].evidence_ids == ()
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW + timedelta(seconds=1),
    )
    assert breaker.state is CircuitBreakerState.HALF_OPEN
    assert breaker.last_success_at is None
    assert breaker.half_open_probe_claim_digest is not None
    assert breaker.consecutive_failure_count == 1


def test_prior_decision_and_empty_planning_trace_stay_unchanged() -> None:
    prepared = _prepare(capability=_AVAILABILITY)
    before = prepared["conversations"].get(prepared["auth"].conversation_id)
    assert before is not None
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_AVAILABILITY, operation="search_catalog"),
    )
    assert result.prior_decision_preserved is True
    after = prepared["conversations"].get(prepared["auth"].conversation_id)
    assert after is not None
    assert after.decision_context == before.decision_context
    assert after.decision_context is not None
    assert after.decision_context.decision_id == prepared["auth"].decision_id
    assert empty_execution_trace(prepared["plan"].plan_id).to_dict()["attempted"] is False
    assert empty_execution_trace(prepared["plan"].plan_id).steps == ()


def test_sqlite_outcome_survives_a_new_session(tmp_path: Path) -> None:
    reset_sync_engine()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'shopify-execution.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    auth, plan, registry, catalog, routing, markets = _plan()
    OperationalAuthorizedExecutionRepository(session_factory=factory).bind(
        authorization_idempotency_key=auth.idempotency_key,
        authorization_id=auth.authorization_id,
        authorization_version=auth.authorization_version,
        decision_id=auth.decision_id,
        plan_id=plan.plan_id,
        now=_NOW,
    )
    conversations = SqlAlchemyConversationRepository(
        session_factory=factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    _seed(conversations, auth)
    claim_service = operational_live_start_claims(factory, token_factory=_token_factory())
    claim = claim_service.claim(
        _claim_request(
            auth,
            plan,
            registry,
            catalog,
            routing,
            markets,
            now=_NOW,
            capability=_DISCOVERY,
        )
    )
    assert claim.claimed is True
    transport = FakeCatalogTransport(_ok(_product(currency="USD")))
    outcome = operational_shopify_execution(
        factory,
        transport,
        clock=_frozen_clock(_NOW),
    ).execute(
        ShopifyCatalogAttempt(
            permit=_PERMIT,
            authorization=auth,
            owner=_owner(),
            plan=plan,
            step=_step(plan, _DISCOVERY),
            source=_SOURCE,
            operation="search_catalog",
            catalog_query="wireless earbuds",
            claim_capability=claim.claim_capability or "",
            harness_operational_status=ConnectorOperationalStatus.AVAILABLE,
        )
    )
    assert outcome.durable_success is True
    assert len(transport.calls) == 1
    reloaded = OperationalAuthorizedExecutionRepository(session_factory=factory).get(
        claim.execution_id or ""
    )
    assert reloaded is not None
    assert reloaded.state == "completed"
    assert reloaded.trace is not None
    assert reloaded.trace.evaluated_offer_count == 1
    assert reloaded.returned_currencies == ("USD",)
    assert reloaded.raw_response_persisted is False
    assert reloaded.claim_digest is None
    encoded = _encoded(reloaded)
    assert "structuredContent" not in encoded
    assert "checkout_url" not in encoded
    engine.dispose()
    reset_sync_engine()


def test_urllib_transport_uses_the_five_second_timeout_without_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","result":{"structuredContent":{}}}'

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def _open_http(request, timeout=None):  # noqa: ANN001
        captured["timeout"] = timeout
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        return _Response()

    monkeypatch.setattr(
        "app.research.shopify_global_catalog_transport._open_http",
        _open_http,
    )
    result = UrllibJsonTransport().post_json(
        GLOBAL_CATALOG_ENDPOINT,
        anonymous_http_headers(),
        {"jsonrpc": "2.0"},
        SHOPIFY_HTTP_TIMEOUT_SECONDS,
    )
    assert captured["timeout"] == 5.0
    assert captured["url"] == GLOBAL_CATALOG_ENDPOINT
    assert result.status_code == 200
    assert result.payload is not None
    assert result.raw_body_persisted is False
    production = FakeCatalogTransport(_ok(_product()))
    blocked = execute_production_shopify_catalog(production)
    assert production.calls == []
    assert blocked.transport_invoked is False


def test_service_clock_separates_start_finish_and_checked_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, datetime] = {}
    real = normalize_shopify_global_catalog_offer

    def _spy(*args, **kwargs):
        seen["checked_at"] = kwargs["checked_at"]
        return real(*args, **kwargs)

    monkeypatch.setattr(
        "app.research.shopify_global_catalog_execution.normalize_shopify_global_catalog_offer",
        _spy,
    )
    prepared = _prepare(capability=_DISCOVERY)
    start = _NOW
    finish = _NOW + timedelta(seconds=3)
    observed: dict[str, datetime | None] = {}

    class _Watch(FakeCatalogTransport):
        def post_json(self, endpoint, headers, payload, timeout_seconds):
            row = prepared["executions"].get(prepared["claim"].execution_id or "")
            assert row is not None
            observed["started"] = row.attempt_started_at
            assert row.state == "running"
            return super().post_json(endpoint, headers, payload, timeout_seconds)

    transport = _Watch(_ok(_product(currency="USD")))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_DISCOVERY, operation="search_catalog"),
        clock=_clock_sequence(start, finish),
    )
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=finish,
    )
    assert result.durable_success is True
    assert observed["started"] == start
    assert seen["checked_at"] == finish
    assert stored is not None
    assert stored.attempt_started_at == start
    assert stored.finished_at == finish
    assert stored.trace is not None
    assert stored.trace.steps[0].started_at == start
    assert stored.trace.steps[0].finished_at == finish
    assert stored.trace.steps[0].evidence_ids == ()
    assert breaker.last_success_at == finish
    assert breaker.last_attempt_at == finish

    failed = _prepare(capability=_PRICING)
    failed_finish = _NOW + timedelta(seconds=4)
    failed_result = _run(
        failed,
        FakeCatalogTransport(CatalogTransportResult(status_code=0, payload=None, timed_out=True)),
        _attempt(failed, capability=_PRICING, operation="get_product"),
        clock=_clock_sequence(_NOW, failed_finish),
    )
    failed_breaker = failed["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=failed_finish,
    )
    assert failed_result.outcome == "timed_out"
    assert failed_result.persisted is True
    assert failed_breaker.last_success_at is None
    assert failed_breaker.last_attempt_at == failed_finish
    assert failed_breaker.last_failure_category is ConnectorFailureKind.TIMEOUT


def test_claim_expiring_during_transport_does_not_commit_or_update_breaker() -> None:
    prepared = _prepare(capability=_OFFER)
    finish = _NOW + EXECUTION_CLAIM_LEASE
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_OFFER, operation="search_catalog"),
        clock=_clock_sequence(_NOW, finish),
    )
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=finish,
    )
    assert len(transport.calls) == 1
    assert result.transport_invoked is True
    assert result.persisted is False
    assert result.durable_success is False
    assert result.block_reason == "execution_claim_expired"
    assert result.state == "running"
    assert stored is not None
    assert stored.state == "running"
    assert stored.attempt_started_at == _NOW
    assert stored.finished_at is None
    assert stored.outcome is None
    assert stored.trace is None
    assert breaker.last_success_at is None
    assert breaker.last_attempt_at is None
    assert breaker.consecutive_failure_count == 0

    timed_out = _prepare(capability=_PRICING)
    timeout_transport = FakeCatalogTransport(
        CatalogTransportResult(status_code=0, payload=None, timed_out=True)
    )
    timeout_result = _run(
        timed_out,
        timeout_transport,
        _attempt(timed_out, capability=_PRICING, operation="get_product"),
        clock=_clock_sequence(_NOW, finish),
    )
    timeout_breaker = timed_out["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=finish,
    )
    assert len(timeout_transport.calls) == 1
    assert timeout_result.persisted is False
    assert timeout_result.durable_success is False
    assert timeout_result.block_reason == "execution_claim_expired"
    assert timeout_breaker.last_failure_category is None
    assert timeout_breaker.consecutive_failure_count == 0
    assert timed_out["executions"].get(timed_out["claim"].execution_id or "").state == (  # type: ignore[union-attr]
        "running"
    )


def test_half_open_probe_expiring_during_transport_does_not_commit() -> None:
    prepared = _prepare(capability=_DISCOVERY, half_open=True)
    breaker = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=_NOW,
    )
    probe_expiry = _NOW + timedelta(seconds=7)
    prepared["reliability"].save(
        replace(breaker, half_open_probe_expires_at=probe_expiry),
        expected_revision=breaker.revision,
    )
    transport = FakeCatalogTransport(_ok(_product()))
    result = _run(
        prepared,
        transport,
        _attempt(prepared, capability=_DISCOVERY, operation="search_catalog"),
        clock=_clock_sequence(_NOW, probe_expiry),
    )
    stored = prepared["executions"].get(prepared["claim"].execution_id or "")
    current = prepared["reliability"].load(
        SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        _MARKET,
        now=probe_expiry,
    )
    assert len(transport.calls) == 1
    assert result.transport_invoked is True
    assert result.persisted is False
    assert result.durable_success is False
    assert result.block_reason == "half_open_probe_expired"
    assert stored is not None
    assert stored.state == "running"
    assert stored.outcome is None
    assert current.state is CircuitBreakerState.HALF_OPEN
    assert current.last_success_at is None
    assert current.half_open_probe_claim_digest is not None
    assert current.half_open_probe_expires_at == probe_expiry


def test_normalized_offer_digests_are_stable_and_are_not_evidence_ids() -> None:
    first = _prepare(capability=_DISCOVERY)
    second = _prepare(capability=_AVAILABILITY)
    product = _product(currency="USD")
    first_result = _run(
        first,
        FakeCatalogTransport(_ok(product)),
        _attempt(first, capability=_DISCOVERY, operation="search_catalog"),
    )
    second_result = _run(
        second,
        FakeCatalogTransport(_ok(product)),
        _attempt(second, capability=_AVAILABILITY, operation="search_catalog"),
    )
    left = first["executions"].get(first["claim"].execution_id or "")
    right = second["executions"].get(second["claim"].execution_id or "")
    assert first_result.durable_success is True
    assert second_result.durable_success is True
    assert left is not None and right is not None
    assert left.normalized_offer_digests == right.normalized_offer_digests
    assert left.evidence_ids == ()
    assert right.evidence_ids == ()
    assert left.trace is not None and right.trace is not None
    assert left.trace.steps[0].evidence_ids == ()
    assert left.normalized_offer_digests[0] not in _encoded(left.trace)
    assert "checkout_url" not in left.normalized_offer_digests[0]


def test_trace_evidence_ids_are_not_offer_counts_or_digests() -> None:
    empty = ResearchExecutionTraceStep(
        plan_id="plan-trace",
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        requested_capability=_DISCOVERY,
        market=_MARKET,
        source=_SOURCE,
        attempted=True,
        attempt_status="succeeded",
        started_at=_NOW,
        finished_at=_NOW + timedelta(seconds=1),
        evaluated_offer_count=1,
    )
    mismatched = ResearchExecutionTraceStep(
        plan_id="plan-trace",
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        requested_capability=_DISCOVERY,
        market=_MARKET,
        source=_SOURCE,
        attempted=True,
        attempt_status="succeeded",
        evidence_ids=("research-evidence:offer-1",),
        started_at=_NOW,
        finished_at=_NOW + timedelta(seconds=1),
        evaluated_offer_count=2,
    )
    assert empty.evidence_ids == ()
    assert empty.evaluated_offer_count == 1
    assert mismatched.evidence_ids == ("research-evidence:offer-1",)
    with pytest.raises(ValueError, match="normalized offer digests are not evidence ids"):
        ResearchExecutionTraceStep(
            plan_id="plan-trace",
            provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
            requested_capability=_DISCOVERY,
            market=_MARKET,
            source=_SOURCE,
            attempted=True,
            attempt_status="succeeded",
            evidence_ids=("ab" * 32,),
            started_at=_NOW,
            finished_at=_NOW + timedelta(seconds=1),
            evaluated_offer_count=1,
        )
    with pytest.raises(ValueError, match="unattempted steps cannot have execution facts"):
        ResearchExecutionTraceStep(
            plan_id="plan-trace",
            provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
            requested_capability=_DISCOVERY,
            evidence_ids=("research-evidence:offer-1",),
        )
    with pytest.raises(ValueError, match="cannot invent evaluated offers"):
        ResearchExecutionTraceStep(
            plan_id="plan-trace",
            provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
            requested_capability=_DISCOVERY,
            market=_MARKET,
            source=_SOURCE,
            attempted=True,
            attempt_status="failed",
            evidence_ids=("research-evidence:offer-1",),
            started_at=_NOW,
            finished_at=_NOW + timedelta(seconds=1),
            error_category="timeout",
        )


@pytest.mark.parametrize(
    ("reason", "timed_out"),
    [
        (ConnectionRefusedError("connection refused"), False),
        (OSError("network unreachable"), False),
        (TimeoutError("timed out"), True),
    ],
)
def test_urllib_urlerror_is_unavailable_unless_it_is_a_timeout(
    monkeypatch: pytest.MonkeyPatch,
    reason: Exception,
    timed_out: bool,
) -> None:
    def _open_http(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(
        "app.research.shopify_global_catalog_transport._open_http",
        _open_http,
    )
    result = UrllibJsonTransport().post_json(
        GLOBAL_CATALOG_ENDPOINT,
        anonymous_http_headers(),
        {"jsonrpc": "2.0"},
        SHOPIFY_HTTP_TIMEOUT_SECONDS,
    )
    assert result.timed_out is timed_out
    assert result.transport_unavailable is not timed_out
    assert result.malformed is False
    assert result.payload is None
    assert result.raw_body_persisted is False


@pytest.mark.parametrize("status_code", [429, 503, 401, 403])
def test_urllib_non_json_http_error_keeps_the_status(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    def _open_http(request, timeout=None):  # noqa: ANN001
        del timeout
        raise urllib.error.HTTPError(
            request.full_url,
            status_code,
            "error",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"<html>not json</html>"),
        )

    monkeypatch.setattr(
        "app.research.shopify_global_catalog_transport._open_http",
        _open_http,
    )
    result = UrllibJsonTransport().post_json(
        GLOBAL_CATALOG_ENDPOINT,
        anonymous_http_headers(),
        {"jsonrpc": "2.0"},
        SHOPIFY_HTTP_TIMEOUT_SECONDS,
    )
    assert result.status_code == status_code
    assert result.malformed is True
    assert result.transport_unavailable is False
    assert result.timed_out is False
    assert result.payload is None


def test_urllib_http_200_non_json_is_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b"not-json"

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(
        "app.research.shopify_global_catalog_transport._open_http",
        lambda *_args, **_kwargs: _Response(),
    )
    result = UrllibJsonTransport().post_json(
        GLOBAL_CATALOG_ENDPOINT,
        anonymous_http_headers(),
        {"jsonrpc": "2.0"},
        SHOPIFY_HTTP_TIMEOUT_SECONDS,
    )
    assert result.status_code == 200
    assert result.malformed is True
    assert result.transport_unavailable is False
    assert result.payload is None
