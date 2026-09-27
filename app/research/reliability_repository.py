"""Repository for research-provider breaker state.

The production implementation uses the existing ``operational_entities``
store and compare-and-swap. No new table is required. The in-memory
implementation is for tests and does not survive process restart.

Authorized execution records are not stored here. That durability decision
is deferred to a later Sprint 38 slice. This module does not call Shopify
or any other connector.
"""

from __future__ import annotations

from dataclasses import replace
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
    """Production factory. This is the persisted breaker, not an in-memory dict."""

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
