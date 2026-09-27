"""Durable authorized-execution preparation records.

Production rows use the existing ``operational_entities`` table and the
namespace ``research.authorized_executions``. No new table and no migration
are required. The lookup identity is ``authorized_execution_id``, which is
already a one-way digest of the server authorization key. The raw key, raw
principal id, session id, browser confirmation token, secrets, and Shopify
payloads are not stored.

The only durable state entered in this slice is ``prepared_unavailable``.
Creating the row does not consume the authorization and does not start a
connector. A new repository, a new service, and a new database session load
the same execution.

Future live start, not implemented here, must be one transaction covering:

A. the durable execution transition out of ``prepared_unavailable``
B. authorization consumption
C. persisted breaker permission
D. connector invocation

Those steps must commit or roll back together. This module does not fake
that transaction.

Before real HTTP is enabled, HALF_OPEN must also enforce one single-probe
lease so multiple workers cannot use the one recovery opportunity at once.
``HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED`` stays false. That lease is not
built here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import RESEARCH_AUTHORIZED_EXECUTIONS
from app.services.research_execution import (
    AuthorizationPlanConflict,
    authorized_execution_id,
)

# Recorded requirement only. The lease is not implemented in this slice.
HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED = False
FUTURE_LIVE_START_BOUNDARY = (
    "durable_execution_live_start",
    "authorization_consumption",
    "persisted_breaker_permission",
    "connector_invocation",
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
    state: Literal["prepared_unavailable"] = "prepared_unavailable"

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
        if self.state != "prepared_unavailable":
            raise ValueError("this slice cannot mark an execution running or completed")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("execution timestamps must be timezone-aware")


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
        with self._ops() as ops:
            return _load(ops, execution_id)

    def row_count(self) -> int:
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
            with self._ops() as ops:
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

        with self._ops() as ops:
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
