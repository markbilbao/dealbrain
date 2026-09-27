"""Sprint 38 engineering foundation. Non-live scripted connectors only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.market.fx import PRODUCTION_FX_CONVERSION_ENABLED
from app.market.support import (
    CertifiedShoppingMarketCatalog,
    production_certified_shopping_markets,
)
from app.research.certification import (
    make_research_provider_certification,
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.research.routing import (
    make_research_provider_routing_policy,
    production_research_provider_routing_policy_catalog,
    research_provider_routing_policy_catalog_for_tests,
)
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.sprint38_live_execution import (
    PRODUCTION_BREAKER_PERSISTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    ConfirmationRefusal,
    ExecutionRefusal,
    ExecutionTrace,
    LiveResearchExecution,
    LiveResearchTarget,
    ResearchExecutionLedger,
    ScriptedConnector,
    ScriptedResponse,
    admit_shopify_catalog_cache,
    aggregate_connector_health,
    assess_live_research_mode,
    destination_reevaluation_execution_connected,
    preserve_prior_decision,
    production_connector_health,
    production_live_mode_assessment,
    refuse_shopify_execution,
    shopify_retry_policy,
)
from app.services.launch_health_service import LaunchHealthService
from app.services.research_execution import execute_research_plan

_NOW = datetime(2026, 9, 26, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.current = _NOW

    def __call__(self) -> datetime:
        value = self.current
        self.current = value + timedelta(seconds=1)
        return value


def _descriptor(
    provider_id: str,
    *,
    test_fixture: bool = False,
    status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    kill_switch: KillSwitch | None = None,
    markets: tuple[str, ...] = ("PH",),
    capabilities: tuple[ResearchCapability, ...] = (ResearchCapability.CURRENT_PRICING,),
    sources: tuple[str, ...] = ("global-catalog",),
) -> ResearchProviderDescriptor:
    return ResearchProviderDescriptor(
        provider_id=provider_id,
        provider_type="test" if test_fixture else "merchant",
        supported_markets=markets,
        supported_capabilities=capabilities,
        supported_sources=sources,
        operational_status=status,
        test_fixture=test_fixture,
        kill_switch=kill_switch or KillSwitch(),
    )


def _catalog(provider_id: str, *, test_fixture: bool) -> object:
    record = make_research_provider_certification(
        provider_id=provider_id,
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        certification_version="v1",
        source="global-catalog",
        test_fixture=test_fixture,
    )
    return research_provider_certification_catalog_for_tests((record,))


def _assess(
    provider_id: str,
    *,
    test_fixture: bool,
    status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    with_routing: bool = True,
    market_certified: bool = True,
    mode: str = "live",
    requested_market: str = "PH",
    requested_capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    requested_source: str = "global-catalog",
    markets: tuple[str, ...] = ("PH",),
    capabilities: tuple[ResearchCapability, ...] = (ResearchCapability.CURRENT_PRICING,),
    sources: tuple[str, ...] = ("global-catalog",),
    certified_markets: frozenset[str] | None = None,
    extra_records: tuple[object, ...] = (),
) -> object:
    provider = StaticResearchProvider(
        _descriptor(
            provider_id,
            test_fixture=test_fixture,
            status=status,
            markets=markets,
            capabilities=capabilities,
            sources=sources,
        )
    )
    routing_records = ()
    if with_routing:
        routing_records = (
            make_research_provider_routing_policy(
                provider_id=provider_id,
                routing_priority=1,
                test_fixture=test_fixture,
            ),
        )
    if certified_markets is None:
        certified_markets = frozenset({"PH"}) if market_certified else frozenset()
    primary = _catalog(provider_id, test_fixture=test_fixture)
    records = (*primary.list_records(), *extra_records)  # type: ignore[attr-defined]
    return assess_live_research_mode(
        mode=mode,
        requested=LiveResearchTarget(
            market=requested_market,
            capability=requested_capability,
            source=requested_source,
        ),
        registry=research_provider_registry_for_tests((provider,)),
        certifications=research_provider_certification_catalog_for_tests(records),
        routing=research_provider_routing_policy_catalog_for_tests(routing_records),
        certified_markets=CertifiedShoppingMarketCatalog(certified_iso_markets=certified_markets),
        trace_handling_present=True,
    )


def test_production_live_mode_stays_closed_without_routing() -> None:
    assessment = production_live_mode_assessment()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert assessment.enabled is False
    assert "mode_not_live" in assessment.reasons
    assert "routing_absent" in assessment.reasons
    assert "provider_not_operationally_eligible" in assessment.reasons
    assert "market_not_eligible" in assessment.reasons
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    assert assessment.fixture_accepted is False


def test_live_mode_fails_closed_for_disabled_provider() -> None:
    assessment = _assess(
        "ph-disabled",
        test_fixture=False,
        status=ConnectorOperationalStatus.DISABLED,
    )
    assert assessment.enabled is False
    assert "provider_not_operationally_eligible" in assessment.reasons


def test_fixture_cannot_satisfy_live_gate() -> None:
    assessment = _assess("fixture-merchant", test_fixture=True)
    assert assessment.enabled is False
    assert "fixture_cannot_satisfy_live_gate" in assessment.reasons
    assert "no_certified_real_connector" in assessment.reasons


def test_request_scoped_live_gate_isolates_market_capability_and_source() -> None:
    ph_price = _assess("ph-real", test_fixture=False)
    assert ph_price.enabled is True
    assert ph_price.reasons == ()
    us_price = _assess(
        "ph-real",
        test_fixture=False,
        requested_market="US",
        certified_markets=frozenset({"PH", "US"}),
    )
    assert us_price.enabled is False
    assert "no_certified_real_connector" in us_price.reasons
    shipping = _assess(
        "ph-real",
        test_fixture=False,
        requested_capability=ResearchCapability.SHIPPING,
    )
    assert shipping.enabled is False
    assert "no_certified_real_connector" in shipping.reasons
    wrong_source = _assess(
        "ph-real",
        test_fixture=False,
        requested_source="other-source",
    )
    assert wrong_source.enabled is False
    assert "no_certified_real_connector" in wrong_source.reasons
    capability_mismatch = _assess(
        "ph-real",
        test_fixture=False,
        capabilities=(ResearchCapability.PRODUCT_DISCOVERY,),
    )
    assert capability_mismatch.enabled is False
    assert "provider_capability_not_supported" in capability_mismatch.reasons
    market_mismatch = _assess(
        "ph-real",
        test_fixture=False,
        markets=("US",),
        certified_markets=frozenset({"PH"}),
    )
    assert market_mismatch.enabled is False
    assert "provider_market_not_supported" in market_mismatch.reasons


def test_unrelated_fixture_does_not_open_or_block_the_requested_gate() -> None:
    fixture = make_research_provider_certification(
        provider_id="fixture-us",
        capability=ResearchCapability.CURRENT_PRICING,
        market="US",
        certification_version="v1",
        source="other-source",
        test_fixture=True,
    )
    ph_price = _assess(
        "ph-real",
        test_fixture=False,
        extra_records=(fixture,),
        certified_markets=frozenset({"PH", "US"}),
    )
    assert ph_price.enabled is True
    assert "fixture_cannot_satisfy_live_gate" not in ph_price.reasons
    us_only = _assess(
        "ph-real",
        test_fixture=False,
        requested_market="US",
        requested_source="other-source",
        extra_records=(fixture,),
        certified_markets=frozenset({"PH", "US"}),
    )
    assert us_only.enabled is False
    assert "fixture_cannot_satisfy_live_gate" in us_only.reasons
    assert (
        production_live_mode_assessment(
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="shopify_global_catalog",
        ).enabled
        is False
    )


def test_synthetic_non_fixture_path_can_open_only_when_every_gate_is_met() -> None:
    assessment = _assess("ph-real", test_fixture=False)
    assert assessment.enabled is True
    assert assessment.reasons == ()
    assert assessment.fixture_accepted is False
    assert production_live_mode_assessment().enabled is False


def test_missing_routing_fails_closed_even_when_mode_is_live() -> None:
    assessment = _assess("ph-real", test_fixture=False, with_routing=False)
    assert assessment.enabled is False
    assert "routing_absent" in assessment.reasons


def test_shopify_execution_does_not_call_shopify() -> None:
    refusal = refuse_shopify_execution()
    assert refusal.called_shopify is False
    assert refusal.http_invoked is False
    assert refusal.execute_invoked is False
    assert "live_shopify_call_not_permitted" in refusal.reasons
    assert "provider_disabled" in refusal.reasons
    assert "routing_absent" in refusal.reasons
    assert "production_profile_undeployed" in refusal.reasons
    assert "public_market_not_activated" in refusal.reasons
    provider = production_research_provider_registry().list_providers()[0]
    with pytest.raises(NotImplementedError, match="Sprint 38"):
        provider.execute(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="plan is required"):
        execute_research_plan(None)  # type: ignore[arg-type]


def test_timeout_429_5xx_retry_breaker_and_kill_switch() -> None:
    clock = _Clock()
    timeout = ScriptedConnector(
        provider_id="timeout-source",
        responses=(ScriptedResponse(kind="timeout"),),
        retry_policy=shopify_retry_policy(),
    )
    limited = ScriptedConnector(
        provider_id="limited-source",
        responses=(
            ScriptedResponse(kind="rate_limit", retry_after_ms=1000),
            ScriptedResponse(kind="success", offers=("offer-a",)),
        ),
    )
    server = ScriptedConnector(
        provider_id="server-source",
        responses=(
            ScriptedResponse(kind="server_error"),
            ScriptedResponse(kind="server_error"),
        ),
    )
    killed = ScriptedConnector(
        provider_id="killed-source",
        responses=(ScriptedResponse(kind="success", offers=("should-not-run",)),),
        kill_switch=KillSwitch(engaged=True, reason="operator"),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-1",
        decision_id="decision-1",
        explicit_confirmation=True,
    )
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (timeout, limited, server, killed),
        certified_connector_count=4,
        now=clock,
        failure_threshold=2,
    )
    by_id = {step.provider_id: step for step in finished.trace.steps}
    assert by_id["timeout-source"].outcome == "timed_out"
    assert by_id["timeout-source"].attempt_count == 1
    assert by_id["timeout-source"].error_category == "timeout"
    assert by_id["limited-source"].outcome == "succeeded"
    assert by_id["limited-source"].attempt_count == 2
    assert by_id["limited-source"].evaluated_offer_count == 1
    assert by_id["server-source"].outcome == "failed"
    assert by_id["server-source"].error_category == "unavailable"
    assert by_id["server-source"].attempt_count == 2
    assert server.circuit_breaker.state is CircuitBreakerState.OPEN
    assert by_id["killed-source"].outcome == "not_attempted"
    assert by_id["killed-source"].error_category == "kill_switch"
    assert killed._index == 0
    assert finished.trace.timed_out_sources == ("timeout-source",)
    assert finished.trace.succeeded_sources == ("limited-source",)
    assert "server-source" in finished.trace.failed_sources
    assert finished.trace.evaluated_offer_count == 1
    assert finished.trace.live is False
    assert finished.replaces_prior_decision is False


def test_credential_failure_is_not_retried() -> None:
    connector = ScriptedConnector(
        provider_id="credential-source",
        responses=(
            ScriptedResponse(kind="credential"),
            ScriptedResponse(kind="success", offers=("x",)),
        ),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-credential",
        decision_id="decision-1",
        explicit_confirmation=True,
    )
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    step = finished.trace.steps[0]
    assert step.outcome == "failed"
    assert step.error_category == "credential"
    assert step.attempt_count == 1
    assert connector._index == 1
    assert finished.no_merchants_available is True


def test_disabled_scripted_provider_is_not_attempted() -> None:
    connector = ScriptedConnector(
        provider_id="disabled-source",
        responses=(ScriptedResponse(kind="success", offers=("x",)),),
        operational_status=ConnectorOperationalStatus.DISABLED,
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-disabled",
        decision_id="decision-1",
        explicit_confirmation=True,
    )
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert finished.trace.steps[0].attempted is False
    assert finished.trace.attempted_sources == ()
    assert connector._index == 0
    assert finished.state == "failed"
    assert finished.no_merchants_available is True


def test_one_connector_failure_is_not_a_multi_merchant_success() -> None:
    connector = ScriptedConnector(
        provider_id="only-source",
        responses=(ScriptedResponse(kind="server_error"),),
        retry_policy=shopify_retry_policy(),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-one",
        decision_id="decision-prior",
        explicit_confirmation=True,
    )
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert finished.state == "failed"
    assert finished.no_merchants_available is True
    assert finished.disclosure is not None
    assert "previous decision is unchanged" in finished.disclosure
    preserved = preserve_prior_decision("decision-prior", finished)
    assert preserved.replaced is False
    assert preserved.current_decision_id == "decision-prior"
    assert finished.trace.evaluated_offer_count == 0


def test_scripted_partial_failure_stays_non_live_and_preserves_decision() -> None:
    ok = ScriptedConnector(
        provider_id="ok-source",
        responses=(ScriptedResponse(kind="success", offers=("one", "two")),),
        retry_policy=shopify_retry_policy(),
    )
    bad = ScriptedConnector(
        provider_id="bad-source",
        responses=(ScriptedResponse(kind="timeout"),),
        retry_policy=shopify_retry_policy(),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-partial",
        decision_id="decision-prior",
        explicit_confirmation=True,
    )
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (ok, bad),
        certified_connector_count=2,
        now=_Clock(),
    )
    assert finished.state == "partial"
    assert finished.trace.live is False
    assert all(step.test_fixture for step in finished.trace.steps)
    assert finished.trace.evaluated_offer_count == 2
    assert "not a live multi-merchant result" in (finished.disclosure or "")
    preserved = preserve_prior_decision("decision-prior", finished)
    assert preserved.replaced is False
    assert preserved.current_decision_id == "decision-prior"


def test_repeated_confirmation_reuses_one_execution() -> None:
    connector = ScriptedConnector(
        provider_id="only-source",
        responses=(ScriptedResponse(kind="success", offers=("only",)),),
        retry_policy=shopify_retry_policy(),
    )
    ledger = ResearchExecutionLedger()
    first = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="same-key",
        decision_id="decision-prior",
        explicit_confirmation=True,
    )
    second = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="same-key",
        decision_id="decision-prior",
        explicit_confirmation=True,
    )
    assert first.execution_id == second.execution_id  # type: ignore[union-attr]
    finished = ledger.run(
        first,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    repeated = ledger.run(
        first,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert repeated.execution_id == finished.execution_id
    assert repeated.state == finished.state
    assert connector._index == 1
    assert finished.replaces_prior_decision is False


def _forged_execution(
    *,
    owner_id: str = "owner-1",
    confirmation_key: str = "forged-key",
    decision_id: str = "decision-forged",
    execution_id: str = "research-exec:forged",
) -> LiveResearchExecution:
    return LiveResearchExecution(
        execution_id=execution_id,
        owner_id=owner_id,
        decision_id=decision_id,
        confirmation_key=confirmation_key,
        state="queued",
        explicit_confirmation=True,
        trace=ExecutionTrace(
            execution_id=execution_id,
            steps=(),
            started_at=None,
            finished_at=None,
        ),
        replaces_prior_decision=False,
        no_merchants_available=False,
        disclosure=None,
    )


def test_forged_queued_execution_cannot_run_without_confirm() -> None:
    connector = ScriptedConnector(
        provider_id="only-source",
        responses=(ScriptedResponse(kind="success", offers=("secret",)),),
        retry_policy=shopify_retry_policy(),
    )
    ledger = ResearchExecutionLedger()
    refused = ledger.run(
        _forged_execution(),
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert isinstance(refused, ExecutionRefusal)
    assert refused.started is False
    assert refused.connectors_invoked is False
    assert connector._index == 0


def test_confirmation_key_does_not_cross_decisions_or_owners() -> None:
    ledger = ResearchExecutionLedger()
    first = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="same-key",
        decision_id="decision-a",
        explicit_confirmation=True,
    )
    again = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="same-key",
        decision_id="decision-a",
        explicit_confirmation=True,
    )
    assert first.execution_id == again.execution_id  # type: ignore[union-attr]
    conflict = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="same-key",
        decision_id="decision-b",
        explicit_confirmation=True,
    )
    assert isinstance(conflict, ConfirmationRefusal)
    assert conflict.reason == "confirmation_key_decision_conflict"
    assert conflict.execution is None
    connector = ScriptedConnector(
        provider_id="only-source",
        responses=(ScriptedResponse(kind="success", offers=("one",)),),
        retry_policy=shopify_retry_policy(),
    )
    forged_other_decision = ledger.run(
        _forged_execution(
            confirmation_key="same-key",
            decision_id="decision-b",
            execution_id="research-exec:other",
        ),
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert isinstance(forged_other_decision, ExecutionRefusal)
    assert connector._index == 0
    other_owner = ledger.confirm(
        owner_id="owner-2",
        confirmation_key="same-key",
        decision_id="decision-a",
        explicit_confirmation=True,
    )
    assert other_owner.execution_id != first.execution_id  # type: ignore[union-attr]
    assert other_owner.owner_id == "owner-2"  # type: ignore[union-attr]


def test_caller_cannot_inflate_connector_count() -> None:
    connector = ScriptedConnector(
        provider_id="only-source",
        responses=(ScriptedResponse(kind="server_error"),),
        retry_policy=shopify_retry_policy(),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-count",
        decision_id="decision-1",
        explicit_confirmation=True,
    )
    refused = ledger.run(
        execution,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=2,
        now=_Clock(),
    )
    assert isinstance(refused, ExecutionRefusal)
    assert refused.reason == "connector_count_mismatch"
    assert connector._index == 0
    finished = ledger.run(
        execution,  # type: ignore[arg-type]
        (connector,),
        certified_connector_count=1,
        now=_Clock(),
    )
    assert finished.state == "failed"  # type: ignore[union-attr]
    assert finished.no_merchants_available is True  # type: ignore[union-attr]


def test_scripted_breaker_is_not_persistent_production_state() -> None:
    assert PRODUCTION_BREAKER_PERSISTED is False
    first = ScriptedConnector(
        provider_id="breaker-source",
        responses=(
            ScriptedResponse(kind="server_error"),
            ScriptedResponse(kind="server_error"),
        ),
    )
    ledger = ResearchExecutionLedger()
    execution = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="confirm-breaker",
        decision_id="decision-1",
        explicit_confirmation=True,
    )
    ledger.run(
        execution,  # type: ignore[arg-type]
        (first,),
        certified_connector_count=1,
        now=_Clock(),
        failure_threshold=2,
    )
    assert first.circuit_breaker.state is CircuitBreakerState.OPEN
    later_request = ScriptedConnector(
        provider_id="breaker-source",
        responses=(ScriptedResponse(kind="success", offers=("fresh",)),),
        retry_policy=shopify_retry_policy(),
    )
    assert later_request.circuit_breaker.state is CircuitBreakerState.CLOSED


def test_no_research_before_explicit_confirmation() -> None:
    ledger = ResearchExecutionLedger()
    refused = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="missing-confirm",
        decision_id="decision-prior",
        explicit_confirmation=False,
    )
    assert isinstance(refused, ConfirmationRefusal)
    assert refused.started is False
    assert refused.execution is None
    created = ledger.confirm(
        owner_id="owner-1",
        confirmation_key="missing-confirm",
        decision_id="decision-prior",
        explicit_confirmation=True,
    )
    assert created.state == "queued"  # type: ignore[union-attr]
    assert created.trace.steps == ()  # type: ignore[union-attr]


def test_readiness_does_not_imply_merchant_health() -> None:
    ready = LaunchHealthService().ready()
    assert ready["ready"] is True
    assert "merchant" not in ready
    health = production_connector_health()
    assert health.readiness_implies_merchant_availability is False
    assert health.merchant_available is False
    assert health.rows[0].operational_status == "disabled"
    assert health.rows[0].healthy is False
    assert health.rows[0].live is False
    killed = _descriptor("ph-killed", kill_switch=KillSwitch(engaged=True))
    report = aggregate_connector_health((killed,))
    assert report.rows[0].kill_switch_engaged is True
    assert report.merchant_available is False


def test_shopify_cache_is_refused_and_destination_flag_stays_false() -> None:
    admission = admit_shopify_catalog_cache()
    assert admission.admitted is False
    assert admission.persistent_index_allowed is False
    assert "do not cache" in admission.reason
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert destination_reevaluation_execution_connected() is False
    assert PRODUCTION_FX_CONVERSION_ENABLED is False
    assert SPRINT_41_STATUS == "UNSTARTED"
    assert production_certified_shopping_markets().to_tuple() == ()
    assert len(production_research_provider_registry().list_providers()) == 1
