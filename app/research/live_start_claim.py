"""Durable live-start claim and HALF_OPEN single-probe lease.

This is the concurrency boundary that must exist before any future connector
HTTP call. It does not perform that call. A successful claim is
``claimed_for_attempt``. It is not running, live, or executing.

One database transaction commits the rows that make the commitment:

- execution claim: one worker owns this shopper execution attempt
- HALF_OPEN probe lease, when the breaker is HALF_OPEN
- exact research authorization: ``authorized_pending_execution`` becomes
  ``consumed`` on the conversation row

A CLOSED breaker does not take the probe lease. The execution claim and the
authorization consumption still commit together. For HALF_OPEN, the same
worker must hold the execution claim, the probe lease, and the consumed
authorization. If any compare-and-swap fails, the transaction rolls back.
There is no partial execution claim, no orphan probe lease, and no consumed
authorization without the claim.

The guarantee is at-most-one active claimant at a time, with a bounded lease
so a crashed worker can be replaced after expiry. It is not exactly-once
external HTTP. A consumed authorization resumes only that same logical
execution. A stale capability cannot write a later outcome:
``validate_active_execution_claim`` and ``validate_active_half_open_probe``
check identity and expiry and do not perform HTTP.

Claiming is not provider health evidence. This module does not call
``record_success`` or ``record_failure`` and does not set attempt, success,
or failure timestamps. Consumption means one logical execution was durably
committed. It does not mean a connector was called.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorOperationalStatus,
    KillSwitch,
    TimeoutPolicy,
)
from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchExecutionPlan,
)
from app.domain.entities.shopping_assistant import ConversationContext, ConversationOwner
from app.domain.exceptions import (
    ConversationOwnershipError,
    ConversationVersionConflictError,
    ShoppingAssistantNotFoundError,
    ShoppingAssistantValidationError,
)
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.errors import PersistenceError
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.market.support import CertifiedShoppingMarketCatalog
from app.research.authorized_execution_repository import (
    AuthorizedExecutionRevisionConflict,
    DurableAuthorizedExecution,
    InMemoryAuthorizedExecutionRepository,
    OperationalAuthorizedExecutionRepository,
)
from app.research.certification import ResearchProviderCertificationCatalog
from app.research.digest import stable_sha256
from app.research.registry import ResearchProviderRegistry
from app.research.reliability_repository import (
    InMemoryResearchReliabilityRepository,
    OperationalResearchReliabilityRepository,
    ReliabilityRevisionConflict,
)
from app.research.reliability_state import (
    HalfOpenProbeAlreadyClaimed,
    ProviderReliabilityState,
    apply_half_open_probe_lease,
    assess_execution_permission,
    half_open_probe_digest,
    probe_lease_is_active,
    reliability_record_key,
)
from app.research.routing import ResearchProviderRoutingPolicyCatalog
from app.research.sprint38_live_execution import LiveResearchTarget, assess_live_research_mode
from app.services.research_authorization import (
    AuthorizationConsumptionConflict,
    validate_consumed_authorization_for_execution_resume,
    validate_research_authorization_for_execution,
)
from app.services.research_execution import authorized_execution_id

# Bounded so a crashed worker cannot hold the attempt forever.
EXECUTION_CLAIM_LEASE = timedelta(seconds=30)
HALF_OPEN_PROBE_LEASE = timedelta(seconds=30)

# Domain TimeoutPolicy and the non-authoritative Shopify candidate both use
# 5_000 ms. The Sprint 32 anonymous harness socket timeout is 30 seconds.
# That harness value equals these leases and must not become the future HTTP
# timeout. No separate measured cleanup duration exists, so the margin below
# is only the strict slack that keeps timeout + margin < lease. It is not a
# second validated Shopify timing, and it does not lengthen the leases.
SHOPIFY_LIVE_HTTP_TIMEOUT = timedelta(milliseconds=TimeoutPolicy().timeout_ms)
LIVE_CONNECTOR_CLEANUP_MARGIN = timedelta(seconds=1)
MAX_LIVE_CONNECTOR_ATTEMPT_TIMEOUT = SHOPIFY_LIVE_HTTP_TIMEOUT

AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM = True
AUTHORIZATION_CONSUMPTION_BOUNDARY = (
    "A successful live-start claim is the server commitment to one logical "
    "connector attempt. The same SQLAlchemy transaction compare-and-swaps "
    "the execution row, the HALF_OPEN probe row when needed, and the "
    "conversation row that holds the exact ResearchAuthorization. "
    "mark_research_authorization_consumed() replaces that pending "
    "authorization with consumed. authorization_version is unchanged. The "
    "conversation persistence_version increments through the existing "
    "conversation compare-and-swap. A failed gate, a failed claim, a failed "
    "probe lease, a conversation version conflict, or a database outage "
    "rolls the transaction back and leaves the authorization "
    "authorized_pending_execution. After commit, a consumed authorization "
    "may resume only that same execution through "
    "validate_consumed_authorization_for_execution_resume(). It cannot "
    "start a second execution. Connector HTTP stays outside this transaction."
)


def _require_connector_timeout_fits_leases() -> None:
    budget = SHOPIFY_LIVE_HTTP_TIMEOUT + LIVE_CONNECTOR_CLEANUP_MARGIN
    if budget >= EXECUTION_CLAIM_LEASE or budget >= HALF_OPEN_PROBE_LEASE:
        raise RuntimeError(
            "future connector timeout plus safety margin must be shorter than "
            "the execution claim lease and the HALF_OPEN probe lease"
        )


_require_connector_timeout_fits_leases()


class ExecutionAlreadyClaimed(Exception):
    """An unexpired claim already belongs to another worker."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"execution_already_claimed for {execution_id}")


@dataclass(frozen=True, slots=True)
class ActiveClaimCheck:
    """Identity check for a later outcome write. This check performs no HTTP."""

    valid: bool
    reason: str | None

    def __post_init__(self) -> None:
        if self.valid and self.reason is not None:
            raise ValueError("a valid claim check cannot carry a reason")
        if not self.valid and not self.reason:
            raise ValueError("an invalid claim check requires a reason")


@dataclass(frozen=True, slots=True)
class LiveStartClaimResult:
    """Internal claim fact. Not a live, running, or executing result.

    ``claim_capability`` and ``probe_capability`` are returned once to the
    claiming worker. They are not shopper-facing and are not stored raw.
    """

    claimed: bool
    execution_id: str | None
    state: str | None
    block_reason: str | None
    claim_expires_at: datetime | None
    half_open_probe_lease_acquired: bool
    connector_invoked: bool = False
    http_invoked: bool = False
    live_execution_started: bool = False
    authorization_consumed: bool = False
    attempted: bool = False
    source_checked: bool = False
    claim_capability: str | None = None
    probe_capability: str | None = None

    def __post_init__(self) -> None:
        if self.connector_invoked or self.http_invoked or self.live_execution_started:
            raise ValueError("a live-start claim must not invoke a connector or HTTP")
        if self.attempted or self.source_checked:
            raise ValueError("a live-start claim must not attempt or check a source")
        if self.authorization_consumed and not self.claimed:
            raise ValueError("authorization is consumed only when the claim commits")
        if self.claimed and self.block_reason is not None:
            raise ValueError("a claimed result cannot carry a block reason")
        if not self.claimed and not self.block_reason:
            raise ValueError("a refused claim requires a block reason")
        if self.claimed and self.state != "claimed_for_attempt":
            raise ValueError("a claim is claimed_for_attempt until a connector starts")
        if self.claimed and self.claim_expires_at is None:
            raise ValueError("a claim requires an expiry")
        if self.half_open_probe_lease_acquired and not self.claimed:
            raise ValueError("a probe lease is not acquired when the claim is refused")
        if self.claimed and not self.claim_capability:
            raise ValueError("the claiming worker must receive the claim capability")
        if self.half_open_probe_lease_acquired and not self.probe_capability:
            raise ValueError("the claiming worker must receive the probe capability")
        if not self.half_open_probe_lease_acquired and self.probe_capability is not None:
            raise ValueError("a probe capability exists only when the lease is acquired")

    def to_public_dict(self) -> dict[str, object]:
        """Shopper-safe facts. The raw claim capability is omitted."""

        return {
            "claimed": self.claimed,
            "execution_id": self.execution_id,
            "state": self.state,
            "block_reason": self.block_reason,
            "claim_expires_at": (
                self.claim_expires_at.isoformat() if self.claim_expires_at is not None else None
            ),
            "half_open_probe_lease_acquired": self.half_open_probe_lease_acquired,
            "connector_invoked": False,
            "http_invoked": False,
            "live_execution_started": False,
            "authorization_consumed": self.authorization_consumed,
            "attempted": False,
            "source_checked": False,
        }


@dataclass(frozen=True, slots=True)
class LiveStartClaimRequest:
    """One future attempt against a prepared execution and an exact plan target."""

    authorization: ResearchAuthorization
    owner: ConversationOwner
    plan: ResearchExecutionPlan
    provider_id: str
    market: str
    capability: ResearchCapability
    source: str
    now: datetime
    operational_status: ConnectorOperationalStatus
    kill_switch: KillSwitch
    registry: ResearchProviderRegistry
    certifications: ResearchProviderCertificationCatalog
    routing: ResearchProviderRoutingPolicyCatalog
    certified_markets: CertifiedShoppingMarketCatalog
    mode: str


@dataclass(frozen=True, slots=True)
class _AuthorizationConsumption:
    """Exact pending authorization the claim transaction will replace."""

    conversation_id: str
    owner: ConversationOwner
    authorization_id: str
    authorization_version: int
    decision_id: str
    canonical_context_version: int
    proposal_id: str
    proposal_version: int
    scope_digest: str
    idempotency_key: str
    expected_version: int
    now: datetime


@dataclass(frozen=True, slots=True)
class _ClaimObservation:
    execution: DurableAuthorizedExecution
    expected_execution_revision: int
    breaker: ProviderReliabilityState | None
    expected_breaker_revision: int | None
    claim_capability: str
    probe_capability: str | None
    consumption: _AuthorizationConsumption | None


class ClaimTransaction(Protocol):
    """One unit of work for the execution, breaker, and conversation rows."""

    def lock_for_claim(self) -> None: ...

    def load_execution(self, execution_id: str) -> DurableAuthorizedExecution | None: ...

    def reload_execution(self, execution_id: str) -> DurableAuthorizedExecution | None: ...

    def load_breaker(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState: ...

    def load_conversation(self, conversation_id: str) -> ConversationContext | None: ...

    def consume_authorization(
        self,
        consumption: _AuthorizationConsumption,
    ) -> ConversationContext: ...

    def cas_execution(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution: ...

    def cas_breaker(
        self,
        state: ProviderReliabilityState,
        *,
        expected_revision: int,
    ) -> ProviderReliabilityState: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class InMemoryClaimTransaction:
    """Test double. Writes use revision compare-and-swap, not a process mutex.

    Rollback restores only the rows this transaction itself changed, so a
    committed peer is left in place.
    """

    def __init__(
        self,
        executions: InMemoryAuthorizedExecutionRepository,
        reliability: InMemoryResearchReliabilityRepository,
        conversations: InMemoryConversationRepository,
    ) -> None:
        self._executions = executions
        self._reliability = reliability
        self._conversations = conversations
        self._exec_previous: dict[str, DurableAuthorizedExecution | None] = {}
        self._rel_previous: dict[str, tuple[str, str, ProviderReliabilityState | None]] = {}
        self._conv_previous: dict[str, ConversationContext | None] = {}

    def lock_for_claim(self) -> None:
        return None

    def load_execution(self, execution_id: str) -> DurableAuthorizedExecution | None:
        return self._executions.get(execution_id)

    def reload_execution(self, execution_id: str) -> DurableAuthorizedExecution | None:
        return self._executions.get(execution_id)

    def load_breaker(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        return self._reliability.load(provider_id, market, now=now)

    def load_conversation(self, conversation_id: str) -> ConversationContext | None:
        return self._conversations.get(conversation_id)

    def consume_authorization(self, consumption: _AuthorizationConsumption) -> ConversationContext:
        if consumption.conversation_id not in self._conv_previous:
            self._conv_previous[consumption.conversation_id] = self._conversations.get(
                consumption.conversation_id
            )
        return self._conversations.consume_research_authorization(
            consumption.conversation_id,
            owner=consumption.owner,
            authorization_id=consumption.authorization_id,
            authorization_version=consumption.authorization_version,
            decision_id=consumption.decision_id,
            canonical_context_version=consumption.canonical_context_version,
            proposal_id=consumption.proposal_id,
            proposal_version=consumption.proposal_version,
            scope_digest=consumption.scope_digest,
            idempotency_key=consumption.idempotency_key,
            expected_version=consumption.expected_version,
            now=consumption.now,
        )

    def cas_execution(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        if record.execution_id not in self._exec_previous:
            self._exec_previous[record.execution_id] = self._executions.get(record.execution_id)
        return self._executions.cas_replace(record, expected_revision=expected_revision)

    def cas_breaker(
        self,
        state: ProviderReliabilityState,
        *,
        expected_revision: int,
    ) -> ProviderReliabilityState:
        key = reliability_record_key(state.provider_id, state.market)
        if key not in self._rel_previous:
            stored = self._reliability.row_count(state.provider_id, state.market) == 1
            previous = (
                self._reliability.load(state.provider_id, state.market, now=state.updated_at)
                if stored
                else None
            )
            self._rel_previous[key] = (state.provider_id, state.market, previous)
        return self._reliability.save(state, expected_revision=expected_revision)

    def commit(self) -> None:
        self._exec_previous.clear()
        self._rel_previous.clear()
        self._conv_previous.clear()

    def rollback(self) -> None:
        for execution_id, previous in self._exec_previous.items():
            self._executions.restore_row(execution_id, previous)
        for provider_id, market, previous in self._rel_previous.values():
            self._reliability.restore_row(provider_id, market, previous)
        for conversation_id, previous in self._conv_previous.items():
            self._conversations.restore_row(conversation_id, previous)
        self._exec_previous.clear()
        self._rel_previous.clear()
        self._conv_previous.clear()

    def close(self) -> None:
        return None


class OperationalClaimTransaction:
    """Production unit of work. One session commits the claim rows or none."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session = session_factory()
        self._executions = OperationalAuthorizedExecutionRepository(session=self._session)
        self._reliability = OperationalResearchReliabilityRepository(self._session)
        self._conversations = SqlAlchemyConversationRepository(session=self._session)
        self._closed = False

    def lock_for_claim(self) -> None:
        """Hold the SQLite write lock before the first read.

        A deferred read can observe the conversation commit and miss the
        execution commit from the same peer transaction. ``BEGIN IMMEDIATE``
        makes the second worker wait until that commit is visible together.
        """

        bind = self._session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            self._session.execute(text("BEGIN IMMEDIATE"))

    def load_execution(self, execution_id: str) -> DurableAuthorizedExecution | None:
        return self._executions.get(execution_id)

    def reload_execution(self, execution_id: str) -> DurableAuthorizedExecution | None:
        self._session.expire_all()
        return self._executions.get(execution_id)

    def load_breaker(
        self,
        provider_id: str,
        market: str,
        *,
        now: datetime,
    ) -> ProviderReliabilityState:
        return self._reliability.load(provider_id, market, now=now)

    def load_conversation(self, conversation_id: str) -> ConversationContext | None:
        return self._conversations.get(conversation_id)

    def consume_authorization(self, consumption: _AuthorizationConsumption) -> ConversationContext:
        return self._conversations.consume_research_authorization(
            consumption.conversation_id,
            owner=consumption.owner,
            authorization_id=consumption.authorization_id,
            authorization_version=consumption.authorization_version,
            decision_id=consumption.decision_id,
            canonical_context_version=consumption.canonical_context_version,
            proposal_id=consumption.proposal_id,
            proposal_version=consumption.proposal_version,
            scope_digest=consumption.scope_digest,
            idempotency_key=consumption.idempotency_key,
            expected_version=consumption.expected_version,
            now=consumption.now,
        )

    def cas_execution(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        return self._executions.cas_replace(record, expected_revision=expected_revision)

    def cas_breaker(
        self,
        state: ProviderReliabilityState,
        *,
        expected_revision: int,
    ) -> ProviderReliabilityState:
        return self._reliability.save(state, expected_revision=expected_revision)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        if not self._closed:
            self._session.close()
            self._closed = True


class LiveStartClaimService:
    """Claim one prepared execution. The clock and token factory are injected."""

    conversations: InMemoryConversationRepository | None

    def __init__(
        self,
        transaction_factory: Callable[[], ClaimTransaction],
        *,
        token_factory: Callable[[], str],
        claim_lease: timedelta = EXECUTION_CLAIM_LEASE,
        probe_lease: timedelta = HALF_OPEN_PROBE_LEASE,
    ) -> None:
        self._transactions = transaction_factory
        self._tokens = token_factory
        self._claim_lease = claim_lease
        self._probe_lease = probe_lease
        self.conversations = None

    def claim(self, request: LiveStartClaimRequest) -> LiveStartClaimResult:
        """Observe, then commit, in one transaction. No connector call."""

        transaction = self._transactions()
        try:
            try:
                transaction.lock_for_claim()
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused("claim_persistence_unavailable", execution_id=None)
            observed = self._observe(transaction, request)
            return self._finish(transaction, observed)
        finally:
            transaction.close()

    def claim_racing(
        self,
        requests: Sequence[LiveStartClaimRequest],
    ) -> tuple[LiveStartClaimResult, ...]:
        """Observe every request before any commit.

        Production workers call ``claim``. This ordering makes the compare-and-swap
        race deterministic. The database or repository revision is still the
        guarantee. An in-process mutex is not.
        """

        transactions = [self._transactions() for _ in requests]
        try:
            observed = [
                self._observe(transaction, request)
                for transaction, request in zip(transactions, requests, strict=True)
            ]
            return tuple(
                self._finish(transaction, item)
                for transaction, item in zip(transactions, observed, strict=True)
            )
        finally:
            for transaction in transactions:
                transaction.close()

    def _observe(
        self,
        transaction: ClaimTransaction,
        request: LiveStartClaimRequest,
    ) -> LiveStartClaimResult | _ClaimObservation:
        try:
            return self._observe_claim(transaction, request)
        except (PersistenceError, OperationalError, DBAPIError):
            transaction.rollback()
            return _refused("claim_persistence_unavailable", execution_id=None)

    def _observe_claim(
        self,
        transaction: ClaimTransaction,
        request: LiveStartClaimRequest,
    ) -> LiveStartClaimResult | _ClaimObservation:
        execution_id = authorized_execution_id(request.authorization.idempotency_key)
        execution = transaction.load_execution(execution_id)
        if execution is None:
            return _refused("execution_not_prepared", execution_id=execution_id)
        pin = _pin_reason(execution, request)
        if pin is not None:
            return _refused(pin, execution_id=execution.execution_id, state=execution.state)
        if not _plan_target_matches(request):
            return _refused(
                "plan_target_mismatch",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        if _claim_is_active(execution, now=request.now):
            return _refused(
                "execution_already_claimed",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        breaker = transaction.load_breaker(request.provider_id, request.market, now=request.now)
        blocked = _gate_reason(request, breaker)
        if blocked is not None:
            return _refused(blocked, execution_id=execution.execution_id, state=execution.state)
        permission = assess_execution_permission(
            breaker,
            operational_status=_effective_status(request),
            kill_switch=_effective_kill_switch(request),
            now=request.now,
        )
        if permission.breaker.state is CircuitBreakerState.HALF_OPEN and probe_lease_is_active(
            permission.breaker,
            now=request.now,
        ):
            return _refused(
                "half_open_probe_already_claimed",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        claim_capability = self._tokens()
        try:
            next_execution = apply_execution_claim(
                execution,
                now=request.now,
                lease=self._claim_lease,
                claim_capability=claim_capability,
            )
        except ExecutionAlreadyClaimed:
            return _refused(
                "execution_already_claimed",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        next_breaker: ProviderReliabilityState | None = None
        probe_capability: str | None = None
        if permission.breaker.state is CircuitBreakerState.HALF_OPEN:
            probe_capability = self._tokens()
            try:
                next_breaker = apply_half_open_probe_lease(
                    permission.breaker,
                    now=request.now,
                    lease=self._probe_lease,
                    claim_capability=probe_capability,
                )
            except HalfOpenProbeAlreadyClaimed:
                return _refused(
                    "half_open_probe_already_claimed",
                    execution_id=execution.execution_id,
                    state=execution.state,
                )
        elif permission.breaker.state is not CircuitBreakerState.CLOSED:
            return _refused(
                "circuit_open",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        commitment = _authorization_commitment(
            transaction,
            request,
            execution,
            claim_active=False,
        )
        if isinstance(commitment, LiveStartClaimResult):
            return commitment
        return _ClaimObservation(
            execution=next_execution,
            expected_execution_revision=execution.revision,
            breaker=next_breaker,
            expected_breaker_revision=None if next_breaker is None else breaker.revision,
            claim_capability=claim_capability,
            probe_capability=probe_capability,
            consumption=commitment,
        )

    def _finish(
        self,
        transaction: ClaimTransaction,
        observed: LiveStartClaimResult | _ClaimObservation,
    ) -> LiveStartClaimResult:
        if isinstance(observed, LiveStartClaimResult):
            transaction.rollback()
            return observed
        execution_id = observed.execution.execution_id
        try:
            stored = transaction.cas_execution(
                observed.execution,
                expected_revision=observed.expected_execution_revision,
            )
            acquired = False
            if observed.breaker is not None and observed.expected_breaker_revision is not None:
                transaction.cas_breaker(
                    observed.breaker,
                    expected_revision=observed.expected_breaker_revision,
                )
                acquired = True
            if observed.consumption is not None:
                transaction.consume_authorization(observed.consumption)
            transaction.commit()
        except AuthorizedExecutionRevisionConflict:
            transaction.rollback()
            current = transaction.load_execution(execution_id)
            return _refused(
                "execution_already_claimed",
                execution_id=execution_id,
                state=None if current is None else current.state,
            )
        except ReliabilityRevisionConflict:
            transaction.rollback()
            current = transaction.load_execution(execution_id)
            return _refused(
                "half_open_probe_already_claimed",
                execution_id=execution_id,
                state=None if current is None else current.state,
            )
        except (
            ConversationVersionConflictError,
            AuthorizationConsumptionConflict,
            ConversationOwnershipError,
            ShoppingAssistantNotFoundError,
            ShoppingAssistantValidationError,
        ):
            transaction.rollback()
            current = transaction.load_execution(execution_id)
            return _refused(
                "authorization_consumption_conflict",
                execution_id=execution_id,
                state=None if current is None else current.state,
            )
        except (PersistenceError, OperationalError, DBAPIError):
            transaction.rollback()
            return _refused("claim_persistence_unavailable", execution_id=execution_id)
        return LiveStartClaimResult(
            claimed=True,
            execution_id=stored.execution_id,
            state=stored.state,
            block_reason=None,
            claim_expires_at=stored.claim_expires_at,
            half_open_probe_lease_acquired=acquired,
            authorization_consumed=observed.consumption is not None,
            claim_capability=observed.claim_capability,
            probe_capability=observed.probe_capability,
        )


def in_memory_live_start_claims(
    executions: InMemoryAuthorizedExecutionRepository | None = None,
    reliability: InMemoryResearchReliabilityRepository | None = None,
    conversations: InMemoryConversationRepository | None = None,
    *,
    token_factory: Callable[[], str],
) -> tuple[
    LiveStartClaimService,
    InMemoryAuthorizedExecutionRepository,
    InMemoryResearchReliabilityRepository,
]:
    """Test service over the in-memory doubles. A new service keeps the rows."""

    execution_store = executions or InMemoryAuthorizedExecutionRepository()
    reliability_store = reliability or InMemoryResearchReliabilityRepository()
    conversation_store = conversations or InMemoryConversationRepository()
    service = LiveStartClaimService(
        lambda: InMemoryClaimTransaction(
            execution_store,
            reliability_store,
            conversation_store,
        ),
        token_factory=token_factory,
    )
    service.conversations = conversation_store
    return service, execution_store, reliability_store


def operational_live_start_claims(
    session_factory: sessionmaker[Session],
    *,
    token_factory: Callable[[], str],
) -> LiveStartClaimService:
    """Production-shaped service. Each claim opens its own session."""

    return LiveStartClaimService(
        lambda: OperationalClaimTransaction(session_factory),
        token_factory=token_factory,
    )


def execution_claim_digest(claim_capability: str) -> str:
    """Opaque digest. Callers keep the raw capability only in memory."""

    if len(claim_capability) < 16:
        raise ValueError("claim capability must be an opaque token")
    return stable_sha256({"kind": "sprint38_execution_claim_v1", "capability": claim_capability})


def apply_execution_claim(
    current: DurableAuthorizedExecution,
    *,
    now: datetime,
    lease: timedelta,
    claim_capability: str,
) -> DurableAuthorizedExecution:
    """Move a prepared or expired execution to ``claimed_for_attempt``.

    Plan and authorization pins are not arguments and cannot change here.
    The repository compare-and-swap assigns the next revision.
    """

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if lease <= timedelta(0):
        raise ValueError("execution claim lease must be bounded and positive")
    if _claim_is_active(current, now=now):
        raise ExecutionAlreadyClaimed(current.execution_id)
    return replace(
        current,
        state="claimed_for_attempt",
        claimed_at=now,
        claim_expires_at=now + lease,
        claim_digest=execution_claim_digest(claim_capability),
        updated_at=now,
    )


def validate_active_execution_claim(
    record: DurableAuthorizedExecution,
    *,
    claim_capability: str,
    now: datetime,
) -> ActiveClaimCheck:
    """Accept only the current unexpired capability. Performs no HTTP."""

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if record.state != "claimed_for_attempt":
        return ActiveClaimCheck(False, "execution_not_claimed")
    if record.claim_expires_at is None or now >= record.claim_expires_at:
        return ActiveClaimCheck(False, "execution_claim_expired")
    try:
        expected = execution_claim_digest(claim_capability)
    except ValueError:
        return ActiveClaimCheck(False, "execution_claim_identity_mismatch")
    if record.claim_digest != expected:
        return ActiveClaimCheck(False, "execution_claim_identity_mismatch")
    return ActiveClaimCheck(True, None)


def validate_active_half_open_probe(
    state: ProviderReliabilityState,
    *,
    claim_capability: str,
    now: datetime,
) -> ActiveClaimCheck:
    """Accept only the current unexpired HALF_OPEN probe capability. No HTTP."""

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if state.state is not CircuitBreakerState.HALF_OPEN:
        return ActiveClaimCheck(False, "half_open_probe_not_active")
    if not probe_lease_is_active(state, now=now):
        return ActiveClaimCheck(False, "half_open_probe_expired")
    try:
        expected = half_open_probe_digest(claim_capability)
    except ValueError:
        return ActiveClaimCheck(False, "half_open_probe_identity_mismatch")
    if state.half_open_probe_claim_digest != expected:
        return ActiveClaimCheck(False, "half_open_probe_identity_mismatch")
    return ActiveClaimCheck(True, None)


def _claim_is_active(record: DurableAuthorizedExecution, *, now: datetime) -> bool:
    return (
        record.state == "claimed_for_attempt"
        and record.claim_expires_at is not None
        and now < record.claim_expires_at
    )


def _authorization_commitment(
    transaction: ClaimTransaction,
    request: LiveStartClaimRequest,
    execution: DurableAuthorizedExecution,
    *,
    claim_active: bool,
) -> _AuthorizationConsumption | None | LiveStartClaimResult:
    """Load the exact authorization. Pending rows are consumed; consumed rows resume.

    ``None`` means this claim reclaims an expired execution and must not consume
    the authorization again. A ``LiveStartClaimResult`` is a refusal. No
    connector call happens here.
    """

    conversation = transaction.load_conversation(request.authorization.conversation_id)
    if conversation is None:
        return _refused(
            "authorization_conversation_missing",
            execution_id=execution.execution_id,
            state=execution.state,
        )
    if conversation.owner is None or not conversation.owner.has_same_identity(request.owner):
        return _refused(
            "wrong_owner",
            execution_id=execution.execution_id,
            state=execution.state,
        )
    stored = _exact_stored_authorization(conversation, request.authorization)
    if isinstance(stored, str):
        return _refused(stored, execution_id=execution.execution_id, state=execution.state)
    if stored.status == "consumed":
        if not _claim_is_active(execution, now=request.now):
            latest = transaction.reload_execution(execution.execution_id)
            if latest is not None:
                execution = latest
        if _claim_is_active(execution, now=request.now):
            return _refused(
                "execution_already_claimed",
                execution_id=execution.execution_id,
                state=execution.state,
            )
        resume = validate_consumed_authorization_for_execution_resume(
            stored,
            owner=request.owner,
            conversation_id=request.plan.conversation_id,
            decision_id=request.plan.decision_id,
            canonical_context_version=request.plan.canonical_context_version,
            proposal_id=request.plan.proposal_id,
            proposal_version=request.plan.proposal_version,
            scope_digest=request.plan.scope_digest,
            execution_id=execution.execution_id,
            execution_plan_id=execution.plan_id,
            execution_authorization_id=execution.authorization_id,
            execution_authorization_version=execution.authorization_version,
            execution_decision_id=execution.decision_id,
            execution_state=execution.state,
            claim_active=claim_active,
            requested_plan_id=request.plan.plan_id,
        )
        if not resume.valid:
            return _refused(
                resume.reason,
                execution_id=execution.execution_id,
                state=execution.state,
            )
        return None
    try:
        validation = validate_research_authorization_for_execution(
            stored,
            owner=request.owner,
            conversation_id=request.plan.conversation_id,
            decision_id=request.plan.decision_id,
            canonical_context_version=request.plan.canonical_context_version,
            expected_scope_digest=request.plan.scope_digest,
            expected_proposal_id=request.plan.proposal_id,
            expected_proposal_version=request.plan.proposal_version,
        )
    except ShoppingAssistantNotFoundError:
        return _refused(
            "wrong_owner",
            execution_id=execution.execution_id,
            state=execution.state,
        )
    if not validation.valid:
        reason = validation.reason or "invalid_status"
        return _refused(reason, execution_id=execution.execution_id, state=execution.state)
    return _AuthorizationConsumption(
        conversation_id=conversation.conversation_id,
        owner=request.owner,
        authorization_id=stored.authorization_id,
        authorization_version=stored.authorization_version,
        decision_id=stored.decision_id,
        canonical_context_version=stored.canonical_context_version,
        proposal_id=stored.proposal_id,
        proposal_version=stored.proposal_version,
        scope_digest=stored.scope_digest,
        idempotency_key=stored.idempotency_key,
        expected_version=conversation.persistence_version,
        now=request.now,
    )


def _exact_stored_authorization(
    conversation: ConversationContext,
    presented: ResearchAuthorization,
) -> ResearchAuthorization | str:
    """Return the one authorization with this id, or a bounded mismatch reason."""

    matches = [
        item
        for item in conversation.research_authorizations
        if item.authorization_id == presented.authorization_id
    ]
    if len(matches) != 1:
        return "authorization_not_found"
    stored = matches[0]
    same = (
        stored.authorization_version == presented.authorization_version
        and stored.conversation_id == presented.conversation_id
        and stored.decision_id == presented.decision_id
        and stored.canonical_context_version == presented.canonical_context_version
        and stored.proposal_id == presented.proposal_id
        and stored.proposal_version == presented.proposal_version
        and stored.scope_digest == presented.scope_digest
        and stored.idempotency_key == presented.idempotency_key
        and stored.owner_binding == presented.owner_binding
    )
    if not same:
        return "authorization_identity_mismatch"
    return stored


def _pin_reason(
    execution: DurableAuthorizedExecution,
    request: LiveStartClaimRequest,
) -> str | None:
    plan = request.plan
    authorization = request.authorization
    if plan.plan_id != execution.plan_id:
        return "authorization_plan_conflict"
    if (
        plan.authorization_id != execution.authorization_id
        or plan.authorization_version != execution.authorization_version
        or plan.decision_id != execution.decision_id
        or plan.authorization_id != authorization.authorization_id
        or plan.authorization_version != authorization.authorization_version
        or plan.decision_id != authorization.decision_id
    ):
        return "execution_pin_mismatch"
    return None


def _plan_target_matches(request: LiveStartClaimRequest) -> bool:
    return any(
        step.provider_id == request.provider_id
        and step.market == request.market
        and step.capability == request.capability
        and request.source in step.source_identities
        for step in request.plan.eligible_steps
    )


def _gate_reason(
    request: LiveStartClaimRequest,
    breaker: ProviderReliabilityState,
) -> str | None:
    assessment = assess_live_research_mode(
        mode=request.mode,
        requested=LiveResearchTarget(
            market=request.market,
            capability=request.capability,
            source=request.source,
        ),
        registry=request.registry,
        certifications=request.certifications,
        routing=request.routing,
        certified_markets=request.certified_markets,
        trace_handling_present=True,
    )
    if "fixture_cannot_satisfy_live_gate" in assessment.reasons:
        return "fixture_cannot_satisfy_live_gate"
    if not assessment.enabled:
        earlier = [
            reason
            for reason in assessment.reasons
            if reason != "provider_not_operationally_eligible"
        ]
        if earlier:
            return earlier[0]
    decision = assess_execution_permission(
        breaker,
        operational_status=_effective_status(request),
        kill_switch=_effective_kill_switch(request),
        now=request.now,
    )
    if not decision.execution_permitted:
        return decision.block_reason
    if not assessment.enabled:
        return assessment.reasons[0]
    return None


def _effective_status(request: LiveStartClaimRequest) -> ConnectorOperationalStatus:
    status = request.operational_status
    provider = request.registry.get(request.provider_id)
    if provider is None:
        return status
    descriptor_status = provider.descriptor.operational_status
    if descriptor_status is not ConnectorOperationalStatus.AVAILABLE:
        return descriptor_status
    return status


def _effective_kill_switch(request: LiveStartClaimRequest) -> KillSwitch:
    if request.kill_switch.engaged:
        return request.kill_switch
    provider = request.registry.get(request.provider_id)
    if provider is not None and provider.descriptor.kill_switch.engaged:
        return provider.descriptor.kill_switch
    return request.kill_switch


def _refused(
    reason: str,
    *,
    execution_id: str | None,
    state: str | None = None,
) -> LiveStartClaimResult:
    return LiveStartClaimResult(
        claimed=False,
        execution_id=execution_id,
        state=state,
        block_reason=reason,
        claim_expires_at=None,
        half_open_probe_lease_acquired=False,
    )


@dataclass(frozen=True, slots=True)
class ShopifyAnonymousRequestContract:
    """Validated Anonymous catalog path for the next slice. This is not an HTTP client.

    Production must use the PiqSavi-owned production UCP profile. That profile
    is undeployed and belongs to Sprint 41. This record does not call Shopify.
    """

    endpoint: str
    tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    forbidden_behaviors: tuple[str, ...]
    ships_to_country: str
    address_country: str
    requested_currency: str
    preserve_returned_currency: bool
    offer_view: str
    content_type: str
    accept: str
    user_agent_required: bool
    authorization_header: bool
    signature: bool
    production_ucp_profile_deployed: bool
    http_implemented: bool = False

    def __post_init__(self) -> None:
        if self.http_implemented:
            raise ValueError("this slice must not implement Shopify HTTP")
        if self.authorization_header or self.signature:
            raise ValueError("the anonymous catalog path sends no authorization or signature")
        if self.production_ucp_profile_deployed:
            raise ValueError("the production UCP profile is not deployed in this slice")


def shopify_anonymous_request_contract() -> ShopifyAnonymousRequestContract:
    """Record the existing validated Anonymous path. Does not perform HTTP."""

    from app.research.shopify_global_catalog_ph_probe import (
        FORBIDDEN_LOOKUP_TOOL,
        GET_PRODUCT_TOOL,
        GLOBAL_CATALOG_ENDPOINT,
        OFFER_VIEW,
        PH_COUNTRY,
        PHP_CURRENCY,
        SEARCH_TOOL,
        anonymous_http_headers,
    )
    from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

    headers = anonymous_http_headers()
    if "Authorization" in headers or headers.get("Content-Type") != "application/json":
        raise ValueError("anonymous catalog headers drifted from the validated contract")
    if not headers.get("User-Agent") or headers.get("Accept") != "application/json":
        raise ValueError("anonymous catalog headers require User-Agent and Accept JSON")
    return ShopifyAnonymousRequestContract(
        endpoint=GLOBAL_CATALOG_ENDPOINT,
        tools=(SEARCH_TOOL, GET_PRODUCT_TOOL),
        forbidden_tools=(FORBIDDEN_LOOKUP_TOOL,),
        forbidden_behaviors=(
            "pagination_beyond_first_page",
            "bulk_ids",
            "promoted_or_affiliate_fields",
            "scraping",
        ),
        ships_to_country=PH_COUNTRY,
        address_country=PH_COUNTRY,
        requested_currency=PHP_CURRENCY,
        preserve_returned_currency=True,
        offer_view=OFFER_VIEW,
        content_type=headers["Content-Type"],
        accept=headers["Accept"],
        user_agent_required=True,
        authorization_header=False,
        signature=False,
        production_ucp_profile_deployed=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
        http_implemented=False,
    )
