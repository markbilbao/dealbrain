"""Production research-provider reliability state.

This module is state and failure control. It does not perform HTTP, call a
connector, or mark live execution operational. Transitions take an injected
clock. They do not read the wall clock.

Breaker-worthy failures increment the consecutive count and can open or
re-open the breaker:

- ``TIMEOUT``
- ``UNAVAILABLE``
- ``UNKNOWN``

These categories are recorded and do not increment or open the breaker:

- ``RATE_LIMIT``
- ``QUOTA``
- ``CREDENTIAL``
- ``KILL_SWITCH``
- ``CIRCUIT_OPEN``
- ``PARTIAL``

The certified Shopify path stays one attempt with no retry categories. This
module does not add retries. Kill switch and provider ``DISABLED`` are
stronger than breaker state. Certification, a closed breaker, routing, and
application readiness do not make a provider operationally available.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

from app.core.countries import is_valid_country_code, normalize_country_code
from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.research.digest import stable_sha256

BREAKER_AFFECTING_FAILURES = frozenset(
    {
        ConnectorFailureKind.TIMEOUT,
        ConnectorFailureKind.UNAVAILABLE,
        ConnectorFailureKind.UNKNOWN,
    }
)
BREAKER_NEUTRAL_FAILURES = frozenset(
    {
        ConnectorFailureKind.RATE_LIMIT,
        ConnectorFailureKind.QUOTA,
        ConnectorFailureKind.CREDENTIAL,
        ConnectorFailureKind.KILL_SWITCH,
        ConnectorFailureKind.CIRCUIT_OPEN,
        ConnectorFailureKind.PARTIAL,
    }
)

_CLASSIFIED = BREAKER_AFFECTING_FAILURES | BREAKER_NEUTRAL_FAILURES
if frozenset(ConnectorFailureKind) != _CLASSIFIED or (
    BREAKER_AFFECTING_FAILURES & BREAKER_NEUTRAL_FAILURES
):
    raise RuntimeError("every ConnectorFailureKind must be classified exactly once")


def failure_affects_breaker(kind: ConnectorFailureKind) -> bool:
    """True when this failure category may increment or open the breaker."""

    return kind in BREAKER_AFFECTING_FAILURES


def reliability_record_key(provider_id: str, market: str) -> str:
    """One breaker row per provider and market. No secrets are part of the key."""

    provider = provider_id.strip()
    if not provider or "|" in provider:
        raise ValueError("provider_id is required and cannot contain '|'")
    code = normalize_country_code(market)
    if not code or not is_valid_country_code(code):
        raise ValueError("market must be a valid ISO country code")
    return f"{provider}|{code}"


@dataclass(frozen=True, slots=True)
class BreakerPolicy:
    """Threshold and recovery window. Callers inject the clock separately."""

    failure_threshold: int = 3
    recovery_window_ms: int = 30_000

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_window_ms < 1:
            raise ValueError("recovery_window_ms must be at least 1")


@dataclass(frozen=True, slots=True)
class ProviderReliabilityState:
    """Durable breaker facts for one provider and market.

    ``revision`` 0 means the row has not been stored. The repository assigns
    the next revision on save. This object stores no secrets, principal ids,
    or connector payloads. A HALF_OPEN probe lease stores only an opaque
    digest, never the raw capability presented to the worker.
    """

    provider_id: str
    market: str
    updated_at: datetime
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    consecutive_failure_count: int = 0
    last_failure_category: ConnectorFailureKind | None = None
    opened_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    reopen_at: datetime | None = None
    revision: int = 0
    half_open_probe_claim_digest: str | None = None
    half_open_probe_claimed_at: datetime | None = None
    half_open_probe_expires_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.updated_at, "updated_at")
        provider, market = reliability_record_key(self.provider_id, self.market).split("|", 1)
        object.__setattr__(self, "provider_id", provider)
        object.__setattr__(self, "market", market)
        if self.consecutive_failure_count < 0 or self.revision < 0:
            raise ValueError("failure count and revision must be non-negative")
        for name in (
            "opened_at",
            "last_attempt_at",
            "last_success_at",
            "reopen_at",
            "half_open_probe_claimed_at",
            "half_open_probe_expires_at",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_aware(value, name)
        _validate_probe_lease(self)
        if self.state is CircuitBreakerState.OPEN:
            if self.opened_at is None or self.reopen_at is None:
                raise ValueError("an open breaker requires opened_at and reopen_at")
            if self.consecutive_failure_count < 1:
                raise ValueError("an open breaker requires a failure count")
        elif self.state is CircuitBreakerState.CLOSED:
            if self.opened_at is not None or self.reopen_at is not None:
                raise ValueError("a closed breaker cannot retain an open window")
        elif self.state is not CircuitBreakerState.HALF_OPEN:
            raise ValueError("breaker state is unknown")


def closed_reliability_state(
    provider_id: str,
    market: str,
    *,
    now: datetime,
) -> ProviderReliabilityState:
    """Absent stored row. Closed, revision 0, and not itself a persisted write."""

    return ProviderReliabilityState(
        provider_id=provider_id,
        market=market,
        updated_at=now,
    )


def advance_recovery(
    state: ProviderReliabilityState,
    *,
    now: datetime,
) -> ProviderReliabilityState:
    """Move OPEN to HALF_OPEN once the configured reopen time has arrived."""

    _require_aware(now, "now")
    if state.state is not CircuitBreakerState.OPEN or state.reopen_at is None:
        return state
    if now < state.reopen_at:
        return state
    return replace(state, state=CircuitBreakerState.HALF_OPEN, updated_at=now)


def record_failure(
    state: ProviderReliabilityState,
    kind: ConnectorFailureKind,
    *,
    now: datetime,
    policy: BreakerPolicy,
) -> ProviderReliabilityState:
    """Record a failure. Only breaker-worthy categories can open the breaker."""

    _require_aware(now, "now")
    current = advance_recovery(state, now=now)
    recorded = replace(
        current,
        last_failure_category=kind,
        last_attempt_at=now,
        updated_at=now,
    )
    if not failure_affects_breaker(kind):
        return recorded
    count = recorded.consecutive_failure_count + 1
    if recorded.state is CircuitBreakerState.HALF_OPEN or count >= policy.failure_threshold:
        return replace(
            recorded,
            state=CircuitBreakerState.OPEN,
            consecutive_failure_count=count,
            opened_at=now,
            reopen_at=now + timedelta(milliseconds=policy.recovery_window_ms),
            **_NO_PROBE_LEASE,
        )
    return replace(
        recorded,
        state=CircuitBreakerState.CLOSED,
        consecutive_failure_count=count,
        opened_at=None,
        reopen_at=None,
        **_NO_PROBE_LEASE,
    )


def record_success(
    state: ProviderReliabilityState,
    *,
    now: datetime,
) -> ProviderReliabilityState:
    """A permitted success closes HALF_OPEN and resets the failure count.

    Success does not close an OPEN breaker. An open breaker has not permitted
    an attempt.
    """

    _require_aware(now, "now")
    if state.state is CircuitBreakerState.OPEN:
        return state
    return replace(
        state,
        state=CircuitBreakerState.CLOSED,
        consecutive_failure_count=0,
        opened_at=None,
        reopen_at=None,
        last_success_at=now,
        last_attempt_at=now,
        updated_at=now,
        **_NO_PROBE_LEASE,
    )


@dataclass(frozen=True, slots=True)
class ReliabilityDecision:
    """Reliability gate result. This slice never invokes a connector."""

    execution_permitted: bool
    block_reason: str | None
    breaker: ProviderReliabilityState
    connector_invoked: bool = False
    http_invoked: bool = False
    live_execution_started: bool = False

    def __post_init__(self) -> None:
        if self.connector_invoked or self.http_invoked or self.live_execution_started:
            raise ValueError(
                "reliability decisions must not invoke a connector or start live execution"
            )
        if self.execution_permitted and self.block_reason is not None:
            raise ValueError("a permitted decision cannot carry a block reason")
        if not self.execution_permitted and not self.block_reason:
            raise ValueError("a blocked decision requires a reason")


def assess_execution_permission(
    state: ProviderReliabilityState,
    *,
    operational_status: ConnectorOperationalStatus,
    kill_switch: KillSwitch,
    now: datetime,
) -> ReliabilityDecision:
    """Kill switch, then disabled provider, then the breaker.

    A closed breaker does not override either stronger control. Disengaging
    the kill switch does not make a DISABLED provider executable. HALF_OPEN
    is a domain permission for one later attempt. This function does not
    perform that attempt.
    """

    _require_aware(now, "now")
    if kill_switch.engaged:
        return ReliabilityDecision(
            execution_permitted=False,
            block_reason="kill_switch",
            breaker=state,
        )
    if operational_status is ConnectorOperationalStatus.DISABLED:
        return ReliabilityDecision(
            execution_permitted=False,
            block_reason="provider_disabled",
            breaker=state,
        )
    if operational_status is not ConnectorOperationalStatus.AVAILABLE:
        return ReliabilityDecision(
            execution_permitted=False,
            block_reason="provider_unavailable",
            breaker=state,
        )
    advanced = advance_recovery(state, now=now)
    if advanced.state is CircuitBreakerState.OPEN:
        return ReliabilityDecision(
            execution_permitted=False,
            block_reason="circuit_open",
            breaker=advanced,
        )
    return ReliabilityDecision(
        execution_permitted=True,
        block_reason=None,
        breaker=advanced,
    )


class ReliabilityStateReader(Protocol):
    """Load breaker state. Callers supply the repository. This does not connect."""

    def load(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState: ...


@dataclass(frozen=True, slots=True)
class ResearchProviderHealth:
    """One provider. Certified, eligible, healthy, and live are separate facts.

    ``operationally_available`` is static and runtime eligibility: provider
    status, kill switch, and a closed breaker. ``merchant_available`` is the
    serving contract for merchant research and uses that same eligibility.
    ``healthy`` requires a recorded successful attempt on top of eligibility.
    ``live`` is actual live execution and stays false in this slice.
    """

    provider_id: str
    market: str
    operational_status: str
    kill_switch_engaged: bool
    breaker_state: str
    consecutive_failure_count: int
    last_failure_category: str | None
    last_success_at: datetime | None
    routing_present: bool
    certification_present: bool
    certified: bool
    test_fixture: bool
    operationally_available: bool
    healthy: bool
    merchant_available: bool
    live: bool
    live_block_reasons: tuple[str, ...]
    breaker_revision: int

    def __post_init__(self) -> None:
        available = _merchant_available(
            operational_status=self.operational_status,
            kill_switch_engaged=self.kill_switch_engaged,
            breaker_state=self.breaker_state,
            test_fixture=self.test_fixture,
        )
        if self.operationally_available is not available:
            raise ValueError(
                "operational availability must follow status, kill switch, and breaker"
            )
        if self.merchant_available is not available:
            raise ValueError("merchant availability follows the serving contract")
        if self.healthy is not _evidence_backed_healthy(
            operationally_available=available,
            last_success_at=self.last_success_at,
        ):
            raise ValueError("healthy requires eligibility and a recorded successful attempt")
        if self.live:
            raise ValueError("this reliability slice cannot claim a live provider")
        if self.certified is not self.certification_present:
            raise ValueError("certified mirrors certification presence and nothing else")
        if "live_execution_not_operational" not in self.live_block_reasons:
            raise ValueError("live execution stays not operational")
        if not self.routing_present and "routing_absent" not in self.live_block_reasons:
            raise ValueError("absent routing must keep live execution blocked")


@dataclass(frozen=True, slots=True)
class ResearchProviderHealthReport:
    """Aggregate health. ``live_evidence`` stays false in this slice."""

    rows: tuple[ResearchProviderHealth, ...]
    merchant_available: bool
    live: bool = False
    live_evidence: bool = False

    def __post_init__(self) -> None:
        if self.live or self.live_evidence:
            raise ValueError("aggregated research health must not claim live evidence")
        expected = any(row.merchant_available for row in self.rows)
        if self.merchant_available is not expected:
            raise ValueError("aggregate merchant availability must match the rows")


def build_research_provider_health(
    *,
    provider_id: str,
    market: str,
    operational_status: ConnectorOperationalStatus,
    kill_switch_engaged: bool,
    breaker: ProviderReliabilityState,
    routing_present: bool,
    certification_present: bool,
    test_fixture: bool,
) -> ResearchProviderHealth:
    """Combine authoritative facts. Static availability is not health evidence."""

    available = _operationally_available(
        operational_status=operational_status.value,
        kill_switch_engaged=kill_switch_engaged,
        breaker_state=breaker.state.value,
        test_fixture=test_fixture,
    )
    reasons = ["live_execution_not_operational"]
    if not routing_present:
        reasons.append("routing_absent")
    if not available:
        reasons.append("merchant_unavailable")
    category = breaker.last_failure_category.value if breaker.last_failure_category else None
    return ResearchProviderHealth(
        provider_id=provider_id,
        market=market,
        operational_status=operational_status.value,
        kill_switch_engaged=kill_switch_engaged,
        breaker_state=breaker.state.value,
        consecutive_failure_count=breaker.consecutive_failure_count,
        last_failure_category=category,
        last_success_at=breaker.last_success_at,
        routing_present=routing_present,
        certification_present=certification_present,
        certified=certification_present,
        test_fixture=test_fixture,
        operationally_available=available,
        healthy=_evidence_backed_healthy(
            operationally_available=available,
            last_success_at=breaker.last_success_at,
        ),
        merchant_available=available,
        live=False,
        live_block_reasons=tuple(reasons),
        breaker_revision=breaker.revision,
    )


def aggregate_research_provider_health(
    rows: tuple[ResearchProviderHealth, ...],
) -> ResearchProviderHealthReport:
    """Generic aggregation. A true row is not live evidence."""

    return ResearchProviderHealthReport(
        rows=rows,
        merchant_available=any(row.merchant_available for row in rows),
    )


def production_research_provider_health(
    *,
    now: datetime,
    repository: ReliabilityStateReader,
) -> ResearchProviderHealthReport:
    """Current production providers. Breaker state is loaded from ``repository``.

    A missing row is closed at revision 0. A stored row supplies its state,
    revision, failure count, last failure, and last success. This function
    does not open a database connection and does not accept a substitute
    breaker snapshot.
    """

    from app.research.certification import production_research_provider_certification_catalog
    from app.research.registry import production_research_provider_registry
    from app.research.routing import production_research_provider_routing_policy_catalog

    _require_aware(now, "now")
    certifications = production_research_provider_certification_catalog().list_records()
    routing = production_research_provider_routing_policy_catalog()
    rows: list[ResearchProviderHealth] = []
    for provider in production_research_provider_registry().list_providers():
        descriptor = provider.descriptor
        market = descriptor.supported_markets[0]
        state = repository.load(descriptor.provider_id, market, now=now)
        certified = any(
            record.provider_id == descriptor.provider_id and not record.test_fixture
            for record in certifications
        )
        policy = routing.lookup(descriptor.provider_id)
        rows.append(
            build_research_provider_health(
                provider_id=descriptor.provider_id,
                market=market,
                operational_status=descriptor.operational_status,
                kill_switch_engaged=descriptor.kill_switch.engaged,
                breaker=state,
                routing_present=policy is not None and not policy.test_fixture,
                certification_present=certified,
                test_fixture=descriptor.test_fixture,
            )
        )
    return aggregate_research_provider_health(tuple(rows))


def _operationally_available(
    *,
    operational_status: str,
    kill_switch_engaged: bool,
    breaker_state: str,
    test_fixture: bool,
) -> bool:
    """Status, kill switch, and a closed breaker. Certification is not an input."""

    return (
        operational_status == ConnectorOperationalStatus.AVAILABLE.value
        and not kill_switch_engaged
        and breaker_state == CircuitBreakerState.CLOSED.value
        and not test_fixture
    )


def _merchant_available(
    *,
    operational_status: str,
    kill_switch_engaged: bool,
    breaker_state: str,
    test_fixture: bool,
) -> bool:
    """Serving contract. Eligibility is not a recorded healthy observation."""

    return _operationally_available(
        operational_status=operational_status,
        kill_switch_engaged=kill_switch_engaged,
        breaker_state=breaker_state,
        test_fixture=test_fixture,
    )


def _evidence_backed_healthy(
    *,
    operationally_available: bool,
    last_success_at: datetime | None,
) -> bool:
    """A successful attempt is required. Static status is not health evidence."""

    return operationally_available and last_success_at is not None


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")


_NO_PROBE_LEASE = {
    "half_open_probe_claim_digest": None,
    "half_open_probe_claimed_at": None,
    "half_open_probe_expires_at": None,
}


class HalfOpenProbeAlreadyClaimed(Exception):
    """Another worker holds the unexpired HALF_OPEN recovery lease."""

    def __init__(self, provider_id: str, market: str) -> None:
        self.provider_id = provider_id
        self.market = market
        super().__init__(f"half_open_probe_already_claimed for {provider_id}|{market}")


def half_open_probe_digest(claim_capability: str) -> str:
    """Opaque digest of a probe capability. The raw capability is not stored."""

    if len(claim_capability) < 16:
        raise ValueError("probe capability must be an opaque token")
    return stable_sha256(
        {"kind": "sprint38_half_open_probe_lease_v1", "capability": claim_capability}
    )


def probe_lease_is_active(state: ProviderReliabilityState, *, now: datetime) -> bool:
    """True while one HALF_OPEN probe lease is still inside its window."""

    _require_aware(now, "now")
    expires = state.half_open_probe_expires_at
    return (
        state.state is CircuitBreakerState.HALF_OPEN
        and bool(state.half_open_probe_claim_digest)
        and expires is not None
        and now < expires
    )


def apply_half_open_probe_lease(
    state: ProviderReliabilityState,
    *,
    now: datetime,
    lease: timedelta,
    claim_capability: str,
) -> ProviderReliabilityState:
    """Reserve the one HALF_OPEN recovery slot. This is not a connector attempt.

    CLOSED does not take this lease. OPEN before ``reopen_at`` cannot take it.
    An unexpired lease blocks every other worker. An expired lease may be
    replaced. Success and failure evidence are left unchanged.
    """

    _require_aware(now, "now")
    if lease <= timedelta(0):
        raise ValueError("probe lease must be bounded and positive")
    advanced = advance_recovery(state, now=now)
    if advanced.state is CircuitBreakerState.CLOSED:
        raise ValueError("a closed breaker does not take a half-open probe lease")
    if advanced.state is CircuitBreakerState.OPEN:
        raise ValueError("an open breaker cannot take a probe lease")
    if probe_lease_is_active(advanced, now=now):
        raise HalfOpenProbeAlreadyClaimed(advanced.provider_id, advanced.market)
    return replace(
        advanced,
        half_open_probe_claim_digest=half_open_probe_digest(claim_capability),
        half_open_probe_claimed_at=now,
        half_open_probe_expires_at=now + lease,
        updated_at=now,
    )


def _validate_probe_lease(state: ProviderReliabilityState) -> None:
    digest = state.half_open_probe_claim_digest
    claimed = state.half_open_probe_claimed_at
    expires = state.half_open_probe_expires_at
    present = digest is not None or claimed is not None or expires is not None
    if state.state is not CircuitBreakerState.HALF_OPEN:
        if present:
            raise ValueError("a probe lease exists only while the breaker is half-open")
        return
    if not present:
        return
    if not digest or claimed is None or expires is None:
        raise ValueError("a half-open probe lease requires digest, claimed_at, and expires_at")
    _require_digest(digest, "half_open_probe_claim_digest")
    if expires <= claimed:
        raise ValueError("half-open probe lease expiry must be after claimed_at")


def _require_digest(value: str, field_name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field_name} must be an opaque sha256 digest")
