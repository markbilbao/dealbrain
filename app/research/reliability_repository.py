"""Repository for research-provider breaker state.

The production implementation uses the existing ``operational_entities``
store and compare-and-swap. No new table is required. The in-memory
implementation is for tests and does not survive process restart.

Authorized execution records live in ``authorized_execution_repository``,
not in this breaker store. This module does not call Shopify or any other
connector. Before HTTP, HALF_OPEN still needs one single-probe lease so
multiple workers cannot share the one recovery opportunity. That lease is
not implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities.connector_reliability import (
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.stores import RESEARCH_PROVIDER_RELIABILITY
from app.research.reliability_state import (
    BreakerPolicy,
    ProviderReliabilityState,
    ReliabilityDecision,
    assess_execution_permission,
    closed_reliability_state,
    record_failure,
    record_success,
    reliability_record_key,
)


class ReliabilityRevisionConflict(Exception):
    """A stale revision lost the compare-and-swap. The newer row is unchanged."""

    def __init__(self, provider_id: str, market: str, expected_revision: int) -> None:
        self.provider_id = provider_id
        self.market = market
        self.expected_revision = expected_revision
        super().__init__(
            f"reliability revision conflict for {provider_id}|{market} at {expected_revision}"
        )


class InMemoryResearchReliabilityRepository:
    """Test double. A new instance does not see another instance's rows."""

    persists_across_process_restart = False

    def __init__(self) -> None:
        self._rows: dict[str, ProviderReliabilityState] = {}

    def load(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        key = reliability_record_key(provider_id, market)
        stored = self._rows.get(key)
        if stored is None:
            return closed_reliability_state(provider_id, market, now=now)
        return stored

    def save(
        self,
        state: ProviderReliabilityState,
        *,
        expected_revision: int,
    ) -> ProviderReliabilityState:
        key = reliability_record_key(state.provider_id, state.market)
        current = self._rows.get(key)
        current_revision = 0 if current is None else current.revision
        if current_revision != expected_revision:
            raise ReliabilityRevisionConflict(state.provider_id, state.market, expected_revision)
        stored = replace(state, revision=expected_revision + 1)
        self._rows[key] = stored
        return stored

    def row_count(self, provider_id: str, market: str) -> int:
        key = reliability_record_key(provider_id, market)
        return 1 if key in self._rows else 0


class OperationalResearchReliabilityRepository:
    """Production breaker store. ``seq`` is the revision.

    The caller commits the session. A later session, including one opened
    after process restart against the same database, loads the committed row.
    """

    persists_across_process_restart = True

    def __init__(self, session: Session) -> None:
        self._ops = OperationalStore(session)

    def load(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        key = reliability_record_key(provider_id, market)
        loaded = self._ops.get_versioned(
            RESEARCH_PROVIDER_RELIABILITY,
            key,
            ProviderReliabilityState,
        )
        if loaded is None:
            return closed_reliability_state(provider_id, market, now=now)
        state, seq, _owner = loaded
        if state.revision != seq:
            state = replace(state, revision=seq)
        return state

    def save(
        self,
        state: ProviderReliabilityState,
        *,
        expected_revision: int,
    ) -> ProviderReliabilityState:
        key = reliability_record_key(state.provider_id, state.market)
        stored = replace(state, revision=expected_revision + 1)
        try:
            if expected_revision == 0:
                existing = self._ops.get_versioned(
                    RESEARCH_PROVIDER_RELIABILITY,
                    key,
                    ProviderReliabilityState,
                )
                if existing is not None:
                    raise ReliabilityRevisionConflict(
                        state.provider_id,
                        state.market,
                        expected_revision,
                    )
                self._ops.insert_versioned(
                    RESEARCH_PROVIDER_RELIABILITY,
                    key,
                    stored,
                    version=stored.revision,
                )
                return stored
            updated = self._ops.compare_and_swap(
                RESEARCH_PROVIDER_RELIABILITY,
                key,
                stored,
                expected_version=expected_revision,
                new_version=stored.revision,
            )
        except PersistenceConflictError as exc:
            raise ReliabilityRevisionConflict(
                state.provider_id,
                state.market,
                expected_revision,
            ) from exc
        if not updated:
            raise ReliabilityRevisionConflict(state.provider_id, state.market, expected_revision)
        return stored


def production_reliability_repository(session: Session) -> OperationalResearchReliabilityRepository:
    """Production factory. This is the persisted breaker, not an in-memory dict.

    Durability means a committed row survives a new repository and a new
    database connection. It does not mean production has been deployed, that
    a row already exists, or that the breaker has been live-validated.
    """

    return OperationalResearchReliabilityRepository(session)


type ResearchReliabilityRepository = (
    InMemoryResearchReliabilityRepository | OperationalResearchReliabilityRepository
)


class ResearchReliabilityGate:
    """Service over one repository. Recreating the service keeps the repository rows."""

    def __init__(
        self,
        repository: ResearchReliabilityRepository,
        *,
        policy: BreakerPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or BreakerPolicy()

    @property
    def policy(self) -> BreakerPolicy:
        return self._policy

    @property
    def repository(self) -> ResearchReliabilityRepository:
        return self._repository

    def load(self, provider_id: str, market: str, *, now: datetime) -> ProviderReliabilityState:
        return self._repository.load(provider_id, market, now=now)

    def record_failure(
        self,
        provider_id: str,
        market: str,
        kind: ConnectorFailureKind,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        current = self._repository.load(provider_id, market, now=now)
        updated = record_failure(current, kind, now=now, policy=self._policy)
        return self._repository.save(updated, expected_revision=current.revision)

    def record_success(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        current = self._repository.load(provider_id, market, now=now)
        updated = record_success(current, now=now)
        if updated == current:
            return current
        return self._repository.save(updated, expected_revision=current.revision)

    def permission(
        self,
        provider_id: str,
        market: str,
        *,
        operational_status: ConnectorOperationalStatus,
        kill_switch: KillSwitch,
        now: datetime,
    ) -> ReliabilityDecision:
        current = self._repository.load(provider_id, market, now=now)
        decision = assess_execution_permission(
            current,
            operational_status=operational_status,
            kill_switch=kill_switch,
            now=now,
        )
        if decision.breaker.state != current.state:
            saved = self._repository.save(decision.breaker, expected_revision=current.revision)
            return replace(decision, breaker=saved)
        return decision


@dataclass(frozen=True, slots=True)
class FutureLiveConnectorPermission:
    """Permission for a future live attempt. This object does not call a connector.

    A passed live-mode flag is not sufficient while the persisted breaker,
    kill switch, or provider status blocks the attempt. HTTP remains unwired.
    HALF_OPEN still needs a single-probe lease before any real HTTP attempt.
    """

    permitted: bool
    block_reason: str | None
    reliability: ReliabilityDecision
    live_mode_enabled: bool
    routing_present: bool
    certification_present: bool
    connector_invoked: bool = False
    http_invoked: bool = False
    live_execution_started: bool = False

    def __post_init__(self) -> None:
        if self.connector_invoked or self.http_invoked or self.live_execution_started:
            raise ValueError("future live permission must not invoke a connector")
        if self.permitted and self.block_reason is not None:
            raise ValueError("a permitted future attempt cannot carry a block reason")
        if not self.permitted and not self.block_reason:
            raise ValueError("a blocked future attempt requires a reason")
        if self.permitted and not self.reliability.execution_permitted:
            raise ValueError("live mode cannot override a blocked persisted breaker")
        if self.permitted and not self.live_mode_enabled:
            raise ValueError("a disabled live mode cannot permit a connector attempt")


def assess_persisted_live_permission(
    repository: ResearchReliabilityRepository,
    *,
    provider_id: str,
    market: str,
    operational_status: ConnectorOperationalStatus,
    kill_switch: KillSwitch,
    now: datetime,
    live_mode_enabled: bool,
    routing_present: bool,
    certification_present: bool,
) -> FutureLiveConnectorPermission:
    """Load the persisted breaker and apply it before any future live attempt.

    Routing, certification, and a passed live-mode flag do not override an
    open breaker, an engaged kill switch, or a provider that is not available.
    This function does not perform HTTP.
    """

    reliability = ResearchReliabilityGate(repository).permission(
        provider_id,
        market,
        operational_status=operational_status,
        kill_switch=kill_switch,
        now=now,
    )
    if not reliability.execution_permitted:
        reason = reliability.block_reason
        permitted = False
    elif not routing_present:
        reason = "routing_absent"
        permitted = False
    elif not certification_present:
        reason = "certification_absent"
        permitted = False
    elif not live_mode_enabled:
        reason = "mode_not_live"
        permitted = False
    else:
        reason = None
        permitted = True
    return FutureLiveConnectorPermission(
        permitted=permitted,
        block_reason=reason,
        reliability=reliability,
        live_mode_enabled=live_mode_enabled,
        routing_present=routing_present,
        certification_present=certification_present,
    )
