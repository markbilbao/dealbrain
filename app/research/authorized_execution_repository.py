"""Durable authorized-execution preparation records.

Production rows use the existing ``operational_entities`` table and the
namespace ``research.authorized_executions``. No new table and no migration
are required. The lookup identity is ``authorized_execution_id``, which is
already a one-way digest of the server authorization key. The raw key, raw
principal id, session id, browser confirmation token, secrets, and Shopify
payloads are not stored.

Preparation enters ``prepared_unavailable``. A later live-start claim may
enter ``claimed_for_attempt``. Neither state consumes the authorization or
starts a connector. A new repository, a new service, and a new database
session load the same execution.

Live start is three phases, and connector HTTP is not inside a database
transaction:

Phase 1, one transaction, implemented by ``app.research.live_start_claim``:
validate the durable execution, claim it for one worker, keep the plan and
authorization pins, enforce the persisted breaker, acquire the HALF_OPEN
single-probe lease when applicable, persist that claim, and commit. The
claim state is ``claimed_for_attempt``. It is not running, because no
connector has started.

Phase 2, outside that transaction, is not implemented: only the worker
holding the claim may invoke the connector.

Phase 3, a later transaction, is not implemented: persist the outcome and
trace facts, update breaker state, release the execution and half-open
leases, and reconcile authorization state. ``mark_research_authorization_consumed``
is still not called here. ResearchAuthorization lives inside
``shopping_assistant.conversations`` and ``mark_research_authorization_consumed``
only returns an in-memory replacement. That write is not in this claim
transaction. See ``AUTHORIZATION_CONSUMPTION_BOUNDARY`` in
``live_start_claim``. This design is at-most-one active claimant at a time,
plus expiry and reclaim. It is not an exactly-once external HTTP guarantee.

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

AuthorizedExecutionState = Literal["prepared_unavailable", "claimed_for_attempt"]

# Repository-backed lease and execution claim. Not live execution.
HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED = True
DURABLE_LIVE_START_CLAIM_IMPLEMENTED = True
EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION = False
FUTURE_LIVE_START_PHASES = (
    "transactional_live_start_claim",
    "external_connector_attempt",
    "transactional_outcome_recording",
)
FUTURE_LIVE_START_CLAIM = (
    "validate_durable_execution",
    "single_worker_execution_claim",
    "authorization_single_execution",
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
        if self.state not in {"prepared_unavailable", "claimed_for_attempt"}:
            raise ValueError("execution state must be prepared or claimed for a future attempt")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("execution timestamps must be timezone-aware")
        _validate_claim_fields(self)


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
    if record.state == "prepared_unavailable":
        if present:
            raise ValueError("a prepared execution cannot carry a claim")
        return
    if claimed_at is None or expires_at is None or not digest:
        raise ValueError("a claim requires claimed_at, claim_expires_at, and claim_digest")
    if claimed_at.tzinfo is None or expires_at.tzinfo is None:
        raise ValueError("claim timestamps must be timezone-aware")
    if expires_at <= claimed_at:
        raise ValueError("claim expiry must be after claimed_at")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("claim_digest must be an opaque sha256 digest")


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
