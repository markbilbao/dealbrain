"""Sprint 38 live-research foundation.

Planning stays in Sprint 31. Ask PiqSavi execution identity is the server
``ResearchAuthorization.idempotency_key``. ``ResearchExecutionLedger.confirm``
is scripted chaos-test bookkeeping only. It is not the shopper confirmation
authority and must not accept a client token as the production execution id.

This module adds a fail-closed live-mode gate, scripted non-live traces, and
honest degradation. The authoritative production trace remains
``ResearchExecutionTrace`` in the domain model. ``ExecutionTrace`` here is not
a second production authority.

It does not perform HTTP, call Shopify, enable production routing, deploy a
profile, or mark destination re-evaluation implemented. Deterministic scripted
providers are non-live orchestration tests, not launch evidence.

The scripted circuit breaker is in-memory chaos-test state on that connector
object. It is not a persistent production breaker across shopper requests.
Persistent production breaker hardening remains Sprint 38 work before closure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.domain.entities.connector_reliability import (
    BoundedRetryPolicy,
    CircuitBreakerSnapshot,
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
    TimeoutPolicy,
)
from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    ResearchCapability,
    ResearchProviderCertification,
    ResearchProviderDescriptor,
)
from app.market.destination_reevaluation import live_destination_reevaluation_available
from app.market.support import (
    CertifiedShoppingMarketCatalog,
    production_certified_shopping_markets,
)
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
)
from app.research.digest import stable_sha256
from app.research.registry import ResearchProviderRegistry, production_research_provider_registry
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    production_research_provider_routing_policy_catalog,
)
from app.research.shopify_global_catalog_capability_policy import SHOPIFY_GLOBAL_CATALOG_MARKET
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
)
from app.research.shopify_global_catalog_provider import SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

SPRINT_38_ENGINEERING_STATUS = "IN PROGRESS"
SHOPPING_RESEARCH_EXECUTION_MODE = "disabled"
SHOPIFY_LIVE_CALL_PERMITTED = False
SHOPIFY_PERSISTENT_CACHE_ALLOWED = False
LIVE_RESEARCH_EXECUTION_OPERATIONAL = False
PRODUCTION_BREAKER_PERSISTED = False
_SHOPIFY_REFUSAL_CAPABILITY = ResearchCapability.CURRENT_PRICING

ExecutionState = Literal["queued", "running", "partial", "completed", "failed", "cancelled"]
ScriptedKind = Literal["success", "timeout", "rate_limit", "server_error", "credential"]
NO_MERCHANTS_DISCLOSURE = (
    "No live merchant result is available for this request. Your previous decision is unchanged."
)
_RETRYABLE = {
    ConnectorFailureKind.TIMEOUT: True,
    ConnectorFailureKind.RATE_LIMIT: True,
    ConnectorFailureKind.UNAVAILABLE: True,
    ConnectorFailureKind.CREDENTIAL: False,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class LiveModeAssessment:
    """Whether production live research may run. Default is closed."""

    enabled: bool
    mode: str
    reasons: tuple[str, ...]
    fixture_accepted: bool = False

    def __post_init__(self) -> None:
        if self.enabled and self.reasons:
            raise ValueError("an enabled live mode cannot carry blocking reasons")
        if self.fixture_accepted:
            raise ValueError("a fixture provider cannot satisfy the live gate")


@dataclass(frozen=True, slots=True)
class ShopifyExecutionRefusal:
    """Shopify adapter result. This foundation never performs a live call."""

    provider_id: str
    called_shopify: bool
    http_invoked: bool
    execute_invoked: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.called_shopify or self.http_invoked or self.execute_invoked:
            raise ValueError("Sprint 38 foundation must not call Shopify")


@dataclass(frozen=True, slots=True)
class ExecutionTraceStep:
    """One source attempt. Counts come from the scripted or refused result."""

    provider_id: str
    capability: ResearchCapability
    outcome: Literal["succeeded", "failed", "timed_out", "not_attempted"]
    attempted: bool
    evaluated_offer_count: int
    test_fixture: bool
    live: bool
    error_category: str | None
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int

    def __post_init__(self) -> None:
        if self.live:
            raise ValueError("this foundation cannot record a live source attempt")
        if self.evaluated_offer_count < 0:
            raise ValueError("evaluated offer count cannot be negative")
        if self.outcome != "succeeded" and self.evaluated_offer_count != 0:
            raise ValueError("failed attempts cannot invent evaluated offers")


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """Truthful source accounting. Empty lists stay empty."""

    execution_id: str
    steps: tuple[ExecutionTraceStep, ...]
    started_at: datetime | None
    finished_at: datetime | None

    @property
    def attempted_sources(self) -> tuple[str, ...]:
        return tuple(step.provider_id for step in self.steps if step.attempted)

    @property
    def succeeded_sources(self) -> tuple[str, ...]:
        return tuple(step.provider_id for step in self.steps if step.outcome == "succeeded")

    @property
    def failed_sources(self) -> tuple[str, ...]:
        return tuple(step.provider_id for step in self.steps if step.outcome == "failed")

    @property
    def timed_out_sources(self) -> tuple[str, ...]:
        return tuple(step.provider_id for step in self.steps if step.outcome == "timed_out")

    @property
    def evaluated_offer_count(self) -> int:
        return sum(step.evaluated_offer_count for step in self.steps)

    @property
    def live(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class LiveResearchExecution:
    """Owner-bound execution. Non-live results do not replace a decision."""

    execution_id: str
    owner_id: str
    decision_id: str
    confirmation_key: str
    state: ExecutionState
    explicit_confirmation: bool
    trace: ExecutionTrace
    replaces_prior_decision: bool
    no_merchants_available: bool
    disclosure: str | None

    def __post_init__(self) -> None:
        if self.replaces_prior_decision:
            raise ValueError("this foundation must not replace a prior decision")
        if self.trace.live:
            raise ValueError("execution trace is not live evidence")


@dataclass(frozen=True, slots=True)
class ConfirmationRefusal:
    started: bool
    reason: str
    execution: LiveResearchExecution | None = None

    def __post_init__(self) -> None:
        if self.started or self.execution is not None:
            raise ValueError("refused confirmation must not start research")


@dataclass(frozen=True, slots=True)
class ExecutionRefusal:
    """run() rejected the request before any connector call."""

    started: bool
    reason: str
    connectors_invoked: bool = False

    def __post_init__(self) -> None:
        if self.started or self.connectors_invoked:
            raise ValueError("refused execution must not run connectors")


@dataclass(frozen=True, slots=True)
class LiveResearchTarget:
    """Exact research need. The live gate does not accept a global any-connector flag."""

    market: str
    capability: ResearchCapability
    source: str


@dataclass(frozen=True, slots=True)
class DecisionPreservation:
    prior_decision_id: str
    current_decision_id: str
    replaced: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ScriptedResponse:
    """Deterministic connector reply. Never live evidence."""

    kind: ScriptedKind
    offers: tuple[str, ...] = ()
    retry_after_ms: int | None = None

    def __post_init__(self) -> None:
        if self.kind != "success" and self.offers:
            raise ValueError("unsuccessful scripted responses cannot carry offers")


@dataclass
class ScriptedConnector:
    """Non-live test connector. Must not be registered as production.

    ``circuit_breaker`` changes only on this object during a scripted run.
    That is deterministic chaos-test behavior. ``PRODUCTION_BREAKER_PERSISTED``
    stays false: a later shopper request does not inherit this object.
    """

    provider_id: str
    responses: tuple[ScriptedResponse, ...]
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING
    test_fixture: bool = True
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE
    kill_switch: KillSwitch = field(default_factory=KillSwitch)
    circuit_breaker: CircuitBreakerSnapshot = field(default_factory=CircuitBreakerSnapshot)
    retry_policy: BoundedRetryPolicy = field(
        default_factory=lambda: BoundedRetryPolicy(
            max_attempts=2,
            retry_on=("timeout", "rate_limit", "unavailable"),
        )
    )
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    _index: int = 0

    def __post_init__(self) -> None:
        if not self.test_fixture:
            raise ValueError("scripted connectors are test fixtures and are not live")
        if self.timeout_policy.timeout_ms < 1:
            raise ValueError("timeout_ms must be at least 1")

    def next_response(self) -> ScriptedResponse:
        if self._index >= len(self.responses):
            raise RuntimeError("scripted connector has no remaining responses")
        response = self.responses[self._index]
        self._index += 1
        return response


@dataclass(frozen=True, slots=True)
class ConnectorHealthRow:
    provider_id: str
    operational_status: str
    healthy: bool
    live: bool
    available: bool
    kill_switch_engaged: bool
    breaker_state: str
    test_fixture: bool


@dataclass(frozen=True, slots=True)
class ConnectorHealthReport:
    rows: tuple[ConnectorHealthRow, ...]
    merchant_available: bool
    readiness_implies_merchant_availability: bool = False

    def __post_init__(self) -> None:
        if self.readiness_implies_merchant_availability:
            raise ValueError("application readiness must not imply merchant availability")


@dataclass(frozen=True, slots=True)
class ShopifyCacheAdmission:
    admitted: bool
    persistent_index_allowed: bool
    reason: str

    def __post_init__(self) -> None:
        if self.admitted or self.persistent_index_allowed:
            raise ValueError("Shopify catalog results must not be cached or indexed")


def assess_live_research_mode(
    *,
    mode: str,
    requested: LiveResearchTarget,
    registry: ResearchProviderRegistry,
    certifications: ResearchProviderCertificationCatalog,
    routing: ResearchProviderRoutingPolicyCatalog,
    certified_markets: CertifiedShoppingMarketCatalog,
    trace_handling_present: bool,
) -> LiveModeAssessment:
    """Fail closed unless the exact requested market, capability, and source qualify."""

    reasons: list[str] = []
    if mode != "live":
        reasons.append("mode_not_live")
    if not trace_handling_present:
        reasons.append("trace_handling_absent")
    if requested.market not in certified_markets.certified_iso_markets:
        reasons.append("market_not_eligible")
    matching = [
        record
        for record in certifications.list_records()
        if record.capability == requested.capability
        and record.market == requested.market
        and record.source == requested.source
        and record.source_scope == "exact"
    ]
    real = [
        record for record in matching if record.is_production_eligible and not record.test_fixture
    ]
    if not real:
        reasons.append("no_certified_real_connector")
        if any(record.test_fixture for record in matching):
            reasons.append("fixture_cannot_satisfy_live_gate")
    else:
        reasons.extend(
            _eligibility_gaps(
                real,
                requested=requested,
                registry=registry,
                routing=routing,
            )
        )
    unique = tuple(dict.fromkeys(reasons))
    return LiveModeAssessment(enabled=not unique, mode=mode, reasons=unique, fixture_accepted=False)


def _eligibility_gaps(
    records: list[ResearchProviderCertification],
    *,
    requested: LiveResearchTarget,
    registry: ResearchProviderRegistry,
    routing: ResearchProviderRoutingPolicyCatalog,
) -> tuple[str, ...]:
    """Gaps for the requested target. An unrelated catalog row is ignored."""

    seen: list[str] = []
    for record in records:
        local: list[str] = []
        provider = registry.get(record.provider_id)
        if provider is None:
            local.append("provider_not_registered")
        else:
            local.extend(_technical_support_gaps(provider.descriptor, requested))
            policy = routing.lookup(record.provider_id)
            if policy is None or policy.test_fixture:
                local.append("routing_absent")
            if not provider.descriptor.is_operationally_available:
                local.append("provider_not_operationally_eligible")
        if not local:
            return ()
        for reason in local:
            if reason not in seen:
                seen.append(reason)
    return tuple(seen)


def _technical_support_gaps(
    descriptor: ResearchProviderDescriptor,
    requested: LiveResearchTarget,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if descriptor.test_fixture:
        reasons.append("fixture_cannot_satisfy_live_gate")
    if requested.capability not in descriptor.supported_capabilities:
        reasons.append("provider_capability_not_supported")
    if requested.market not in descriptor.supported_markets:
        reasons.append("provider_market_not_supported")
    if requested.source not in descriptor.supported_sources:
        reasons.append("source_not_supported")
    return tuple(reasons)


def production_live_mode_assessment(
    *,
    capability: ResearchCapability = _SHOPIFY_REFUSAL_CAPABILITY,
    market: str = SHOPIFY_GLOBAL_CATALOG_MARKET,
    source: str = SHOPIFY_GLOBAL_CATALOG_SOURCE,
) -> LiveModeAssessment:
    """Production gate for one exact target. Defaults are the Shopify PH price target."""

    return assess_live_research_mode(
        mode=SHOPPING_RESEARCH_EXECUTION_MODE,
        requested=LiveResearchTarget(market=market, capability=capability, source=source),
        registry=production_research_provider_registry(),
        certifications=production_research_provider_certification_catalog(),
        routing=production_research_provider_routing_policy_catalog(),
        certified_markets=production_certified_shopping_markets(),
        trace_handling_present=True,
    )


def refuse_shopify_execution() -> ShopifyExecutionRefusal:
    """Refuse the certified PH provider before any network or execute() call."""

    registry = production_research_provider_registry()
    provider = registry.get(SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID)
    reasons: list[str] = []
    if provider is None or not provider.descriptor.is_operationally_available:
        reasons.append("provider_disabled")
    if not production_research_provider_routing_policy_catalog().list_records():
        reasons.append("routing_absent")
    if not PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED:
        reasons.append("production_profile_undeployed")
    if not SHOPIFY_LIVE_CALL_PERMITTED:
        reasons.append("live_shopify_call_not_permitted")
    assessment = production_live_mode_assessment(
        capability=_SHOPIFY_REFUSAL_CAPABILITY,
        market=SHOPIFY_GLOBAL_CATALOG_MARKET,
        source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
    )
    if not assessment.enabled:
        reasons.append("live_mode_closed")
    if not production_certified_shopping_markets().is_certified("PH"):
        reasons.append("public_market_not_activated")
    return ShopifyExecutionRefusal(
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        called_shopify=False,
        http_invoked=False,
        execute_invoked=False,
        reasons=tuple(reasons),
    )


def admit_shopify_catalog_cache() -> ShopifyCacheAdmission:
    """Certified Shopify policy: query-time only. Do not cache or index."""

    if SHOPIFY_PERSISTENT_CACHE_ALLOWED:
        raise RuntimeError("Shopify persistent cache is prohibited")
    return ShopifyCacheAdmission(
        admitted=False,
        persistent_index_allowed=False,
        reason="do not cache Shopify Catalog search results or images",
    )


def destination_reevaluation_execution_connected() -> bool:
    """Live destination re-evaluation stays disconnected until evidence exists."""

    return (
        DESTINATION_REEVALUATION_IMPLEMENTED
        and live_destination_reevaluation_available()
        and production_live_mode_assessment(
            capability=_SHOPIFY_REFUSAL_CAPABILITY,
            market=SHOPIFY_GLOBAL_CATALOG_MARKET,
            source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        ).enabled
        and LIVE_RESEARCH_EXECUTION_OPERATIONAL
    )


def _execution_id(owner_id: str, confirmation_key: str) -> str:
    digest = stable_sha256(
        {
            "kind": "sprint38_research_execution_v1",
            "owner_id": owner_id,
            "confirmation_key": confirmation_key,
        }
    )
    return f"research-exec:{digest[:32]}"


class ResearchExecutionLedger:
    """Scripted chaos-test ledger. Not the Ask PiqSavi execution authority.

    Production preparation keys off the server authorization idempotency key
    in ``app.services.research_execution``. A caller confirmation string passed
    here does not authorize a shopper execution.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], LiveResearchExecution] = {}

    def confirm(
        self,
        *,
        owner_id: str,
        confirmation_key: str,
        decision_id: str,
        explicit_confirmation: bool,
    ) -> LiveResearchExecution | ConfirmationRefusal:
        if not explicit_confirmation:
            return ConfirmationRefusal(started=False, reason="explicit_confirmation_required")
        if not owner_id or not confirmation_key or not decision_id:
            return ConfirmationRefusal(started=False, reason="owner_bound_confirmation_required")
        key = (owner_id, confirmation_key)
        existing = self._records.get(key)
        if existing is not None:
            if existing.decision_id != decision_id:
                return ConfirmationRefusal(
                    started=False,
                    reason="confirmation_key_decision_conflict",
                )
            return existing
        execution_id = _execution_id(owner_id, confirmation_key)
        execution = LiveResearchExecution(
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
        self._records[key] = execution
        return execution

    def run(
        self,
        execution: LiveResearchExecution,
        connectors: tuple[ScriptedConnector, ...],
        *,
        certified_connector_count: int,
        now: Callable[[], datetime] = _utcnow,
        failure_threshold: int = 3,
    ) -> LiveResearchExecution | ExecutionRefusal:
        """Run the stored confirmed execution once. A forged execution is refused."""

        current = self._records.get((execution.owner_id, execution.confirmation_key))
        if current is None or not _is_authoritative(current, execution):
            return ExecutionRefusal(started=False, reason="explicit_confirmation_required")
        if current.state != "queued":
            return current
        if certified_connector_count != len(connectors):
            return ExecutionRefusal(started=False, reason="connector_count_mismatch")
        started = now()
        running = _replace(current, state="running")
        steps = tuple(
            _run_connector(connector, now=now, failure_threshold=failure_threshold)
            for connector in connectors
        )
        finished = now()
        trace = ExecutionTrace(
            execution_id=execution.execution_id,
            steps=steps,
            started_at=started,
            finished_at=finished,
        )
        completed = _finish(running, trace, certified_connector_count=certified_connector_count)
        self._records[(execution.owner_id, execution.confirmation_key)] = completed
        return completed


def _is_authoritative(stored: LiveResearchExecution, supplied: LiveResearchExecution) -> bool:
    return (
        stored.explicit_confirmation is True
        and supplied.owner_id == stored.owner_id
        and supplied.confirmation_key == stored.confirmation_key
        and supplied.execution_id == stored.execution_id
        and supplied.decision_id == stored.decision_id
    )


def _replace(execution: LiveResearchExecution, *, state: ExecutionState) -> LiveResearchExecution:
    return LiveResearchExecution(
        execution_id=execution.execution_id,
        owner_id=execution.owner_id,
        decision_id=execution.decision_id,
        confirmation_key=execution.confirmation_key,
        state=state,
        explicit_confirmation=execution.explicit_confirmation,
        trace=execution.trace,
        replaces_prior_decision=False,
        no_merchants_available=execution.no_merchants_available,
        disclosure=execution.disclosure,
    )


def _finish(
    execution: LiveResearchExecution,
    trace: ExecutionTrace,
    *,
    certified_connector_count: int,
) -> LiveResearchExecution:
    succeeded = bool(trace.succeeded_sources)
    attempted = bool(trace.attempted_sources)
    one_connector_down = certified_connector_count <= 1 and not succeeded
    if not attempted or one_connector_down:
        state: ExecutionState = "failed"
        no_merchants = True
        disclosure = NO_MERCHANTS_DISCLOSURE
    elif len(trace.succeeded_sources) < len(trace.attempted_sources):
        state = "partial"
        no_merchants = False
        disclosure = (
            "Some non-live test sources failed. This is not a live multi-merchant result. "
            "The previous decision is unchanged."
        )
    else:
        state = "completed"
        no_merchants = False
        disclosure = None
    return LiveResearchExecution(
        execution_id=execution.execution_id,
        owner_id=execution.owner_id,
        decision_id=execution.decision_id,
        confirmation_key=execution.confirmation_key,
        state=state,
        explicit_confirmation=True,
        trace=trace,
        replaces_prior_decision=False,
        no_merchants_available=no_merchants,
        disclosure=disclosure,
    )


def preserve_prior_decision(
    prior_decision_id: str,
    execution: LiveResearchExecution,
) -> DecisionPreservation:
    """Failure, partial, and non-live completion keep the prior decision."""

    return DecisionPreservation(
        prior_decision_id=prior_decision_id,
        current_decision_id=prior_decision_id,
        replaced=False,
        reason="prior decision preserved",
    )


def _run_connector(
    connector: ScriptedConnector,
    *,
    now: Callable[[], datetime],
    failure_threshold: int,
) -> ExecutionTraceStep:
    started = now()
    if connector.kill_switch.engaged or not _operational(connector):
        return _step(
            connector,
            outcome="not_attempted",
            attempted=False,
            offers=0,
            error=_blocked_reason(connector),
            started=None,
            finished=None,
            attempts=0,
        )
    if connector.circuit_breaker.state == CircuitBreakerState.OPEN:
        return _step(
            connector,
            outcome="not_attempted",
            attempted=False,
            offers=0,
            error=ConnectorFailureKind.CIRCUIT_OPEN.value,
            started=None,
            finished=None,
            attempts=0,
        )
    attempts = 0
    consecutive_failures = 0
    while True:
        response = connector.next_response()
        attempts += 1
        kind = _kind_for(response.kind)
        if response.kind == "success":
            return _step(
                connector,
                outcome="succeeded",
                attempted=True,
                offers=len(response.offers),
                error=None,
                started=started,
                finished=now(),
                attempts=attempts,
            )
        consecutive_failures += 1
        if consecutive_failures >= failure_threshold:
            connector.circuit_breaker = CircuitBreakerSnapshot(
                state=CircuitBreakerState.OPEN,
                reason=kind.value,
            )
        if not _may_retry(connector.retry_policy, kind, attempts):
            outcome: Literal["failed", "timed_out"] = (
                "timed_out" if kind == ConnectorFailureKind.TIMEOUT else "failed"
            )
            return _step(
                connector,
                outcome=outcome,
                attempted=True,
                offers=0,
                error=kind.value,
                started=started,
                finished=now(),
                attempts=attempts,
            )


def _operational(connector: ScriptedConnector) -> bool:
    return (
        connector.operational_status == ConnectorOperationalStatus.AVAILABLE
        and not connector.kill_switch.engaged
        and connector.circuit_breaker.allows_execution
    )


def _blocked_reason(connector: ScriptedConnector) -> str:
    if connector.kill_switch.engaged:
        return ConnectorFailureKind.KILL_SWITCH.value
    if connector.circuit_breaker.state == CircuitBreakerState.OPEN:
        return ConnectorFailureKind.CIRCUIT_OPEN.value
    return "provider_disabled"


def _kind_for(kind: ScriptedKind) -> ConnectorFailureKind:
    if kind == "timeout":
        return ConnectorFailureKind.TIMEOUT
    if kind == "rate_limit":
        return ConnectorFailureKind.RATE_LIMIT
    if kind == "server_error":
        return ConnectorFailureKind.UNAVAILABLE
    if kind == "credential":
        return ConnectorFailureKind.CREDENTIAL
    return ConnectorFailureKind.UNKNOWN


def _may_retry(policy: BoundedRetryPolicy, kind: ConnectorFailureKind, attempts: int) -> bool:
    if attempts >= policy.max_attempts:
        return False
    if not _RETRYABLE.get(kind, False):
        return False
    return kind.value in policy.retry_on


def _step(
    connector: ScriptedConnector,
    *,
    outcome: Literal["succeeded", "failed", "timed_out", "not_attempted"],
    attempted: bool,
    offers: int,
    error: str | None,
    started: datetime | None,
    finished: datetime | None,
    attempts: int,
) -> ExecutionTraceStep:
    return ExecutionTraceStep(
        provider_id=connector.provider_id,
        capability=connector.capability,
        outcome=outcome,
        attempted=attempted,
        evaluated_offer_count=offers,
        test_fixture=True,
        live=False,
        error_category=error,
        started_at=started,
        finished_at=finished,
        attempt_count=attempts,
    )


def aggregate_connector_health(
    descriptors: tuple[ResearchProviderDescriptor, ...],
) -> ConnectorHealthReport:
    """Health is distinct from application readiness."""

    rows: list[ConnectorHealthRow] = []
    merchant_available = False
    for descriptor in descriptors:
        available = descriptor.is_operationally_available and not descriptor.test_fixture
        if available:
            merchant_available = True
        rows.append(
            ConnectorHealthRow(
                provider_id=descriptor.provider_id,
                operational_status=descriptor.operational_status.value,
                healthy=available,
                live=False,
                available=available,
                kill_switch_engaged=descriptor.kill_switch.engaged,
                breaker_state=descriptor.circuit_breaker.state.value,
                test_fixture=descriptor.test_fixture,
            )
        )
    return ConnectorHealthReport(
        rows=tuple(rows),
        merchant_available=merchant_available,
        readiness_implies_merchant_availability=False,
    )


def production_connector_health() -> ConnectorHealthReport:
    descriptors = tuple(
        provider.descriptor for provider in production_research_provider_registry().list_providers()
    )
    return aggregate_connector_health(descriptors)


def shopify_retry_policy() -> BoundedRetryPolicy:
    """Catalog retries would persist a result. The certified path does not retry."""

    return BoundedRetryPolicy(max_attempts=1, retry_on=())


def certification_records_do_not_open_live_mode(
    records: tuple[ResearchProviderCertification, ...],
) -> bool:
    """Helper for tests: records existing is not the live gate."""

    del records
    return production_live_mode_assessment().enabled
