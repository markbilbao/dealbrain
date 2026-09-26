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
    SHOPPING_RESEARCH_EXECUTION_MODE,
    ConfirmationRefusal,
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
) -> ResearchProviderDescriptor:
    return ResearchProviderDescriptor(
        provider_id=provider_id,
        provider_type="test" if test_fixture else "merchant",
        supported_markets=("PH",),
        supported_capabilities=(ResearchCapability.CURRENT_PRICING,),
        supported_sources=("global-catalog",),
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
) -> object:
    provider = StaticResearchProvider(
        _descriptor(provider_id, test_fixture=test_fixture, status=status)
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
    markets = frozenset({"PH"}) if market_certified else frozenset()
    return assess_live_research_mode(
        mode=mode,
        registry=research_provider_registry_for_tests((provider,)),
        certifications=_catalog(provider_id, test_fixture=test_fixture),  # type: ignore[arg-type]
        routing=research_provider_routing_policy_catalog_for_tests(routing_records),
        certified_markets=CertifiedShoppingMarketCatalog(certified_iso_markets=markets),
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
    with pytest.raises(NotImplementedError, match="Sprint 38"):
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
