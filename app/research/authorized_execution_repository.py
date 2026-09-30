"""Durable authorized-execution preparation records.

Production rows use the existing ``operational_entities`` table and the
namespace ``research.authorized_executions``. No new table and no migration
are required. The lookup identity is ``authorized_execution_id``, which is
already a one-way digest of the server authorization key. The raw key, raw
principal id, session id, browser confirmation token, secrets, and Shopify
payloads are not stored.

Preparation enters ``prepared_unavailable`` and does not consume the
authorization. A later live-start claim may enter ``claimed_for_attempt``
and, in the same transaction, consume the exact authorization. Neither state
starts a connector. A new repository, a new service, and a new database
session load the same execution.

Live start is three phases, and connector HTTP is not inside a database
transaction:

Phase 1, one transaction, implemented by ``app.research.live_start_claim``:
validate the durable execution, claim it for one worker, keep the plan and
authorization pins, enforce the persisted breaker, acquire the HALF_OPEN
single-probe lease when applicable, consume the exact research authorization,
compare-and-swap the conversation row, persist that claim, and commit. The
claim state is ``claimed_for_attempt``. It is not running, because no
connector has started. A consumed authorization resumes only that same
execution after the claim expires. It does not start a second execution.

Phase 2, outside that transaction, is implemented by
``app.research.shopify_global_catalog_execution`` for the certified Shopify
catalog path. Only the worker holding the claim may invoke the injected
transport. Production composition does not call it. HTTP stays outside the
database transaction.

Phase 3, a later transaction, persists the outcome and authoritative trace,
updates breaker state, and releases the execution claim. A HALF_OPEN probe
lease is cleared when the attempt outcome is known. An ambiguous post-HTTP
crash does not clear that lease and does not record success. Authorization
is already consumed in phase 1 and is not consumed again. See
``AUTHORIZATION_CONSUMPTION_BOUNDARY`` in ``live_start_claim``. This design
is at-most-one active claimant at a time, plus expiry and reclaim. It is
not an exactly-once external HTTP guarantee. A crash after the attempt-start
commit and before the outcome commit is ``outcome_unknown`` and is not
replayed.

Database unavailability at this boundary becomes
``PersistenceUnavailableError`` via ``translate_db_error``. Preparation then
returns ``blocked_persistence`` and does not fall back to an in-memory ledger.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal, NoReturn

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.research_execution import ResearchExecutionTrace
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session import translate_db_error
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import RESEARCH_AUTHORIZED_EXECUTIONS
from app.services.research_execution import (
    AuthorizationPlanConflict,
    authorized_execution_id,
)

AuthorizedExecutionState = Literal[
    "prepared_unavailable",
    "claimed_for_attempt",
    "running",
    "completed",
    "failed",
    "outcome_unknown",
]
_TERMINAL_EXECUTION_STATES = frozenset({"completed", "failed", "outcome_unknown"})
_CLAIM_STATES = frozenset({"claimed_for_attempt", "running"})

# Repository-backed lease and execution claim. Not live execution.
HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED = True
DURABLE_LIVE_START_CLAIM_IMPLEMENTED = True
EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION = False
# Phase names stay stable. Implementation lives behind the Shopify adapter
# and is not reachable from production composition.
EXTERNAL_CONNECTOR_ATTEMPT_IMPLEMENTED = True
TRANSACTIONAL_OUTCOME_RECORDING_IMPLEMENTED = True
FUTURE_LIVE_START_PHASES = (
    "transactional_live_start_claim",
    "external_connector_attempt",
    "transactional_outcome_recording",
)
FUTURE_LIVE_START_CLAIM = (
    "validate_durable_execution",
    "single_worker_execution_claim",
    "authorization_single_execution",
    "consume_exact_research_authorization",
    "persisted_breaker_permission",
    "half_open_single_probe_lease",
    "persist_live_start_claim",
)


class AuthorizedExecutionRevisionConflict(Exception):
    """A stale revision lost compare-and-swap. The newer row is unchanged."""

    def __init__(self, execution_id: str, expected_revision: int) -> None:
        self.execution_id = execution_id
        self.expected_revision = expected_revision
        super().__init__(
            f"authorized execution revision conflict for {execution_id} at {expected_revision}"
        )


@dataclass(frozen=True, slots=True)
class DurableAuthorizedExecution:
    """One prepared execution. No raw authorization key and no owner material."""

    execution_id: str
    authorization_id: str
    authorization_version: int
    decision_id: str
    plan_id: str
    created_at: datetime
    updated_at: datetime
    revision: int
    state: AuthorizedExecutionState = "prepared_unavailable"
    claimed_at: datetime | None = None
    claim_expires_at: datetime | None = None
    claim_digest: str | None = None
    attempt_started_at: datetime | None = None
    finished_at: datetime | None = None
    attempted_provider_id: str | None = None
    attempted_capability: str | None = None
    attempted_market: str | None = None
    attempted_source: str | None = None
    outcome: str | None = None
    error_category: str | None = None
    evaluated_offer_count: int = 0
    normalized_offer_count: int = 0
    returned_currencies: tuple[str, ...] = ()
    normalized_amount_minors: tuple[int, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    observation_kind: str | None = None
    request_digest: str | None = None
    trace: ResearchExecutionTrace | None = None
    raw_response_persisted: bool = False

    def __post_init__(self) -> None:
        if not self.execution_id.startswith("research-exec:"):
            raise ValueError("execution_id must be the server-derived research execution id")
        if not self.authorization_id:
            raise ValueError("authorization_id is required")
        if self.authorization_version < 1:
            raise ValueError("authorization_version must be at least 1")
        if not self.decision_id or not self.plan_id:
            raise ValueError("decision_id and plan_id are required")
        if self.revision < 1:
            raise ValueError("revision must be at least 1")
        if self.state not in {
            "prepared_unavailable",
            "claimed_for_attempt",
            "running",
            "completed",
            "failed",
            "outcome_unknown",
        }:
            raise ValueError("execution state is unknown")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("execution timestamps must be timezone-aware")
        if self.raw_response_persisted:
            raise ValueError("raw Shopify responses must not be persisted")
        if self.observation_kind == "live":
            raise ValueError("this execution record cannot store a live observation")
        if self.evaluated_offer_count < 0 or self.normalized_offer_count < 0:
            raise ValueError("offer counts cannot be negative")
        _validate_claim_fields(self)
        _validate_attempt_fields(self)


def _translate_store_error(exc: Exception) -> NoReturn:
    """Map driver failures. Plan and revision conflicts keep their own types."""

    if isinstance(exc, (AuthorizationPlanConflict, AuthorizedExecutionRevisionConflict)):
        raise exc
    translated = translate_db_error(exc)
    if translated is not exc:
        raise translated from exc
    raise exc


@contextmanager
def _store_boundary() -> Iterator[None]:
    try:
        yield
    except Exception as exc:
        _translate_store_error(exc)


def _require_same_plan(
    existing: DurableAuthorizedExecution,
    *,
    decision_id: str,
    plan_id: str,
) -> DurableAuthorizedExecution:
    if existing.decision_id != decision_id:
        raise ValueError("authorization identity does not match the stored execution")
    if existing.plan_id != plan_id:
        raise AuthorizationPlanConflict(existing)
    return existing


def _require_same_pins(
    current: DurableAuthorizedExecution,
    record: DurableAuthorizedExecution,
) -> None:
    if record.plan_id != current.plan_id:
        raise AuthorizationPlanConflict(current)
    if (
        record.decision_id != current.decision_id
        or record.authorization_id != current.authorization_id
        or record.authorization_version != current.authorization_version
        or record.execution_id != current.execution_id
    ):
        raise ValueError("authorization identity does not match the stored execution")


def _validate_claim_fields(record: DurableAuthorizedExecution) -> None:
    claimed_at = record.claimed_at
    expires_at = record.claim_expires_at
    digest = record.claim_digest
    present = claimed_at is not None or expires_at is not None or digest is not None
    if record.state == "prepared_unavailable" or record.state in _TERMINAL_EXECUTION_STATES:
        if present:
            raise ValueError("this execution state cannot carry an active claim")
        return
    if record.state not in _CLAIM_STATES:
        raise ValueError("execution state is unknown")
    if claimed_at is None or expires_at is None or not digest:
        raise ValueError("a claim requires claimed_at, claim_expires_at, and claim_digest")
    if claimed_at.tzinfo is None or expires_at.tzinfo is None:
        raise ValueError("claim timestamps must be timezone-aware")
    if expires_at <= claimed_at:
        raise ValueError("claim expiry must be after claimed_at")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("claim_digest must be an opaque sha256 digest")


def _validate_attempt_fields(record: DurableAuthorizedExecution) -> None:
    started = record.attempt_started_at
    finished = record.finished_at
    identity = (
        record.attempted_provider_id,
        record.attempted_capability,
        record.attempted_market,
        record.attempted_source,
    )
    if record.state in {"prepared_unavailable", "claimed_for_attempt"}:
        if started is not None or finished is not None or record.outcome is not None:
            raise ValueError("a claim is not an attempt")
        if any(identity) or record.trace is not None or record.request_digest is not None:
            raise ValueError("a claim cannot store attempt facts")
        if record.evidence_ids or record.returned_currencies or record.normalized_amount_minors:
            raise ValueError("a claim cannot store normalized results")
        if record.evaluated_offer_count or record.normalized_offer_count:
            raise ValueError("a claim cannot store offer counts")
        if record.observation_kind is not None or record.error_category is not None:
            raise ValueError("a claim cannot store an observation or error")
        return
    if started is None or started.tzinfo is None:
        raise ValueError("an attempt requires attempt_started_at")
    if not all(identity):
        raise ValueError("an attempt records provider, capability, market, and source")
    if record.state == "running":
        if finished is not None or record.outcome is not None or record.trace is not None:
            raise ValueError("running has no durable outcome yet")
        if record.evidence_ids or record.evaluated_offer_count or record.normalized_offer_count:
            raise ValueError("running cannot store an outcome count")
        return
    if finished is None or finished.tzinfo is None or finished < started:
        raise ValueError("a terminal attempt requires finished_at")
    if record.trace is None or record.trace.plan_id != record.plan_id:
        raise ValueError("a terminal attempt requires the authoritative trace")
    if record.outcome is None:
        raise ValueError("a terminal attempt requires an outcome")
    if len(record.evidence_ids) != record.evaluated_offer_count:
        raise ValueError("evidence ids must match the evaluated offer count")
    if len(record.returned_currencies) != record.normalized_offer_count:
        raise ValueError("returned currencies must match the normalized offer count")
    if len(record.normalized_amount_minors) != record.normalized_offer_count:
        raise ValueError("normalized amounts must match the normalized offer count")
    if record.evaluated_offer_count != record.normalized_offer_count:
        raise ValueError("evaluated and normalized offer counts must match")
    if record.state == "completed":
        if record.outcome != "succeeded" or record.error_category is not None:
            raise ValueError("completed requires a succeeded outcome")
        if record.evaluated_offer_count < 1:
            raise ValueError("completed requires at least one normalized offer")
        if record.observation_kind != "synthetic":
            raise ValueError("this slice only persists synthetic observations")
    elif record.state == "failed":
        if record.outcome not in {"failed", "timed_out"} or not record.error_category:
            raise ValueError("failed requires a failure outcome and error category")
        if record.evaluated_offer_count:
            raise ValueError("a failed attempt cannot invent offers")
        if record.observation_kind not in {None, "synthetic"}:
            raise ValueError("a failure observation cannot be labeled live")
    elif record.state == "outcome_unknown":
        if record.outcome != "outcome_unknown" or record.error_category != "outcome_unknown":
            raise ValueError("outcome_unknown cannot be labeled success or failure")
        if record.evaluated_offer_count or record.observation_kind is not None:
            raise ValueError("an unknown outcome has no offer and no observation class")
    else:
        raise ValueError("execution state is unknown")


class InMemoryAuthorizedExecutionRepository:
    """Test double. A new instance does not see another instance's rows."""

    persists_across_process_restart = False

    def __init__(self) -> None:
        self._rows: dict[str, DurableAuthorizedExecution] = {}

    def get(self, execution_id: str) -> DurableAuthorizedExecution | None:
        return self._rows.get(execution_id)

    def row_count(self) -> int:
        return len(self._rows)

    def bind(
        self,
        *,
        authorization_idempotency_key: str,
        decision_id: str,
        plan_id: str,
        authorization_id: str,
        authorization_version: int,
        now: datetime,
    ) -> DurableAuthorizedExecution:
        execution_id = authorized_execution_id(authorization_idempotency_key)
        existing = self._rows.get(execution_id)
        if existing is not None:
            return _require_same_plan(existing, decision_id=decision_id, plan_id=plan_id)
        record = DurableAuthorizedExecution(
            execution_id=execution_id,
            authorization_id=authorization_id,
            authorization_version=authorization_version,
            decision_id=decision_id,
            plan_id=plan_id,
            created_at=now,
            updated_at=now,
            revision=1,
        )
        raced = self._rows.get(execution_id)
        if raced is not None:
            return _require_same_plan(raced, decision_id=decision_id, plan_id=plan_id)
        self._rows[execution_id] = record
        return record

    def save(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        current = self._rows.get(record.execution_id)
        current_revision = 0 if current is None else current.revision
        if current_revision != expected_revision or current is None:
            raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
        _require_same_plan(current, decision_id=record.decision_id, plan_id=record.plan_id)
        stored = replace(current, updated_at=record.updated_at, revision=expected_revision + 1)
        self._rows[record.execution_id] = stored
        return stored

    def cas_replace(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        """Compare-and-swap the full row. Pins cannot change."""

        current = self._rows.get(record.execution_id)
        current_revision = 0 if current is None else current.revision
        if current is None or current_revision != expected_revision:
            raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
        _require_same_pins(current, record)
        stored = replace(record, created_at=current.created_at, revision=expected_revision + 1)
        self._rows[record.execution_id] = stored
        return stored

    def restore_row(
        self,
        execution_id: str,
        record: DurableAuthorizedExecution | None,
    ) -> None:
        """Put back the row from before this transaction's write. Test double only."""

        if record is None:
            self._rows.pop(execution_id, None)
        else:
            self._rows[execution_id] = record


class OperationalAuthorizedExecutionRepository(SessionBound):
    """Production preparation store. ``seq`` is the revision.

    A session factory commits on success. A later session, including one
    opened after the repository object is discarded, loads the committed row.
    Persistence failures propagate. This repository does not fall back to an
    in-memory ledger.
    """

    persists_across_process_restart = True

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
    ) -> None:
        super().__init__(session_factory=session_factory, session=session)

    def get(self, execution_id: str) -> DurableAuthorizedExecution | None:
        with _store_boundary(), self._ops() as ops:
            return _load(ops, execution_id)

    def row_count(self) -> int:
        with _store_boundary():
            with self._ops() as ops:
                count = ops._session.scalar(  # noqa: SLF001 — count stays inside the store session
                    select(func.count())
                    .select_from(OperationalEntityModel)
                    .where(OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS)
                )
            return int(count or 0)

    def bind(
        self,
        *,
        authorization_idempotency_key: str,
        decision_id: str,
        plan_id: str,
        authorization_id: str,
        authorization_version: int,
        now: datetime,
    ) -> DurableAuthorizedExecution:
        execution_id = authorized_execution_id(authorization_idempotency_key)
        try:
            with _store_boundary(), self._ops() as ops:
                existing = _load(ops, execution_id)
                if existing is not None:
                    return _require_same_plan(existing, decision_id=decision_id, plan_id=plan_id)
                record = DurableAuthorizedExecution(
                    execution_id=execution_id,
                    authorization_id=authorization_id,
                    authorization_version=authorization_version,
                    decision_id=decision_id,
                    plan_id=plan_id,
                    created_at=now,
                    updated_at=now,
                    revision=1,
                )
                ops.insert_versioned(
                    RESEARCH_AUTHORIZED_EXECUTIONS,
                    execution_id,
                    record,
                    version=1,
                )
                return record
        except PersistenceConflictError:
            with _store_boundary():
                if self._session is not None:
                    self._session.rollback()
                with self._ops() as ops:
                    winner = _load(ops, execution_id)
            if winner is None:
                raise
            return _require_same_plan(winner, decision_id=decision_id, plan_id=plan_id)

    def save(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        """Compare-and-swap one prepared row. Does not change plan or state."""

        with _store_boundary(), self._ops() as ops:
            current = _load(ops, record.execution_id)
            current_revision = 0 if current is None else current.revision
            if current is None or current_revision != expected_revision:
                raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
            _require_same_plan(current, decision_id=record.decision_id, plan_id=record.plan_id)
            stored = replace(current, updated_at=record.updated_at, revision=expected_revision + 1)
            updated = ops.compare_and_swap(
                RESEARCH_AUTHORIZED_EXECUTIONS,
                record.execution_id,
                stored,
                expected_version=expected_revision,
                new_version=stored.revision,
            )
            if not updated:
                raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
            return stored

    def cas_replace(
        self,
        record: DurableAuthorizedExecution,
        *,
        expected_revision: int,
    ) -> DurableAuthorizedExecution:
        """Compare-and-swap the full row, including a live-start claim. Pins stay put."""

        with _store_boundary(), self._ops() as ops:
            current = _load(ops, record.execution_id)
            current_revision = 0 if current is None else current.revision
            if current is None or current_revision != expected_revision:
                raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
            _require_same_pins(current, record)
            stored = replace(record, created_at=current.created_at, revision=expected_revision + 1)
            updated = ops.compare_and_swap(
                RESEARCH_AUTHORIZED_EXECUTIONS,
                record.execution_id,
                stored,
                expected_version=expected_revision,
                new_version=stored.revision,
            )
            if not updated:
                raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)
            return stored


def _load(ops: OperationalStore, execution_id: str) -> DurableAuthorizedExecution | None:
    loaded = ops.get_versioned(
        RESEARCH_AUTHORIZED_EXECUTIONS,
        execution_id,
        DurableAuthorizedExecution,
    )
    if loaded is None:
        return None
    record, seq, _owner = loaded
    if record.revision != seq:
        record = replace(record, revision=seq)
    return record


def production_authorized_execution_repository() -> OperationalAuthorizedExecutionRepository:
    """Production factory. This is the durable preparation binding.

    Durability means a committed row survives a new repository, a new
    service, and a new database connection. It does not mean production has
    been deployed or that live execution has started.
    """

    return OperationalAuthorizedExecutionRepository()
