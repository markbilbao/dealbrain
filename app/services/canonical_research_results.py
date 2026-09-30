"""Integrate a validated research outcome into the existing canonical Results.

``CanonicalDecisionSnapshot`` stays the only Results authority. A successful
production observation appends the next immutable context version for the same
decision and owner. PiqScore and Recommendation snapshots are copied. This
module does not calculate either authority.

Fixture and synthetic evidence cannot create that version. A product outside
the evaluated set, or a variant that does not map exactly, keeps the previous
decision. Failed, timed out, partial, and ``outcome_unknown`` executions do
too.

Evidence insertion, snapshot insertion, and conversation binding are ordered
and idempotent. They do not share one database transaction. A failure does not
delete an immutable snapshot and does not point a conversation at a missing
version. The same execution cannot create a second context version.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import RLock
from typing import Literal, Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.decision_snapshot import (
    CanonicalDecisionSnapshot,
    DecisionEvidenceSnapshot,
)
from app.domain.entities.offer_economics import (
    CanonicalMoneyLine,
    CanonicalOfferEconomics,
)
from app.domain.entities.research_execution import ResearchCapability
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    ConversationContextDriftError,
    ConversationOwnershipError,
    ConversationVersionConflictError,
    DecisionSnapshotConflictError,
    DecisionSnapshotOwnershipError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.infrastructure.persistence.errors import PersistenceConflictError, PersistenceError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import RESEARCH_RESULTS_INTEGRATION
from app.marketplace.freshness.rules import FreshnessStatus, evaluate_freshness
from app.research.authorized_execution_repository import DurableAuthorizedExecution
from app.research.digest import stable_sha256
from app.research.execution_evidence import (
    FixtureEvidenceRejected,
    MissingExecutionEvidence,
    ResearchExecutionEvidence,
)
from app.services.decision_snapshot_service import DecisionSnapshotBinder

IntegrationOutcome = Literal[
    "canonical_results_updated",
    "already_integrated",
    "canonical_reevaluation_required",
    "ambiguous_variant",
    "prior_decision_preserved",
    "wrong_owner",
    "different_decision",
    "evidence_unresolved",
    "fixture_evidence_rejected",
    "snapshot_persistence_failed",
    "conversation_binding_failed",
    "integration_conflict",
]
_PRICE = ResearchCapability.CURRENT_PRICING.value
_UNKNOWN_COMPONENTS = ("shipping", "tax", "import", "voucher", "promotions", "checkout cost")


class _ExecutionReader(Protocol):
    def get(self, execution_id: str) -> DurableAuthorizedExecution | None: ...


class _EvidenceReader(Protocol):
    def get(self, evidence_id: str) -> ResearchExecutionEvidence | None: ...

    def require_production_evidence(self, evidence_id: str) -> ResearchExecutionEvidence: ...


class StaleIntegrationRevision(PersistenceError):
    """A worker lost the integration compare-and-swap or tried to regress state."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"stale results integration revision for {execution_id}")


@dataclass(frozen=True, slots=True)
class ResultsIntegrationRecord:
    """One execution may create at most one next canonical version."""

    execution_id: str
    decision_id: str
    context_version: int
    state: str
    evidence_ids: tuple[str, ...]
    outcome: str
    revision: int = 1

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("integration revision must be at least 1")


_FORWARD_INTEGRATION_STATES = {
    "pending": frozenset({"snapshot_written", "snapshot_failed", "integration_conflict"}),
    "snapshot_written": frozenset({"bound"}),
    "bound": frozenset(),
    "snapshot_failed": frozenset(),
    "integration_conflict": frozenset(),
    "canonical_reevaluation_required": frozenset(),
    "ambiguous_variant": frozenset(),
    "fixture_evidence_rejected": frozenset(),
}


def _integration_regresses(
    existing: ResultsIntegrationRecord,
    proposed: ResultsIntegrationRecord,
) -> bool:
    """True when the proposed row would move backward or rewrite the same state."""

    if (
        existing.execution_id != proposed.execution_id
        or existing.decision_id != proposed.decision_id
    ):
        return True
    if existing.context_version != proposed.context_version:
        return True
    allowed = _FORWARD_INTEGRATION_STATES.get(existing.state)
    if allowed is None:
        return True
    return proposed.state not in allowed


@dataclass(frozen=True, slots=True)
class CanonicalIntegrationResult:
    """Fail-closed integration result. Caller success flags are not an input."""

    outcome: IntegrationOutcome
    decision_id: str
    context_version: int | None
    evidence_ids: tuple[str, ...]
    prior_decision_preserved: bool
    shopper_results_updated: bool

    def __post_init__(self) -> None:
        if self.shopper_results_updated and self.outcome not in {
            "canonical_results_updated",
            "already_integrated",
        }:
            raise ValueError("only an integrated canonical version updates shopper Results")


class InMemoryResultsIntegrationRepository:
    """Idempotency lock for one process. The execution id is the key.

    The process lock is a test aid. Correctness for two service instances is
    the revision compare-and-swap below, not this object's lock.
    """

    persists_across_process_restart = False

    def __init__(self) -> None:
        self._rows: dict[str, ResultsIntegrationRecord] = {}
        self._lock = RLock()

    def get(self, execution_id: str) -> ResultsIntegrationRecord | None:
        with self._lock:
            return self._rows.get(execution_id)

    def insert(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        stored = replace(record, revision=1)
        with self._lock:
            existing = self._rows.get(record.execution_id)
            if existing is not None:
                raise PersistenceConflictError(record.execution_id)
            self._rows[record.execution_id] = stored
        return stored

    def transition(
        self,
        record: ResultsIntegrationRecord,
        *,
        expected_revision: int,
    ) -> ResultsIntegrationRecord:
        stored = replace(record, revision=expected_revision + 1)
        with self._lock:
            existing = self._rows.get(record.execution_id)
            if existing is None:
                raise PersistenceError(f"missing integration {record.execution_id}")
            if existing.revision != expected_revision or _integration_regresses(existing, record):
                raise StaleIntegrationRevision(record.execution_id)
            self._rows[record.execution_id] = stored
        return stored


class OperationalResultsIntegrationRepository(SessionBound):
    """``research.execution_results_integration`` on the existing operational table."""

    persists_across_process_restart = True

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
    ) -> None:
        super().__init__(session_factory=session_factory, session=session)

    def get(self, execution_id: str) -> ResultsIntegrationRecord | None:
        with self._ops() as ops:
            loaded = ops.get_versioned(
                RESEARCH_RESULTS_INTEGRATION,
                execution_id,
                ResultsIntegrationRecord,
            )
        if loaded is None:
            return None
        record, seq, _owner = loaded
        if record.revision != seq:
            return replace(record, revision=seq)
        return record

    def insert(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        stored = replace(record, revision=1)
        try:
            with self._ops() as ops:
                ops.insert_versioned(
                    RESEARCH_RESULTS_INTEGRATION,
                    stored.execution_id,
                    stored,
                    version=1,
                )
        except PersistenceConflictError as exc:
            raise PersistenceConflictError(record.execution_id) from exc
        return stored

    def transition(
        self,
        record: ResultsIntegrationRecord,
        *,
        expected_revision: int,
    ) -> ResultsIntegrationRecord:
        existing = self.get(record.execution_id)
        if existing is None:
            raise PersistenceError(f"missing integration {record.execution_id}")
        if existing.revision != expected_revision or _integration_regresses(existing, record):
            raise StaleIntegrationRevision(record.execution_id)
        stored = replace(record, revision=expected_revision + 1)
        with self._ops() as ops:
            updated = ops.compare_and_swap(
                RESEARCH_RESULTS_INTEGRATION,
                record.execution_id,
                stored,
                expected_version=expected_revision,
                new_version=stored.revision,
            )
        if not updated:
            raise StaleIntegrationRevision(record.execution_id)
        return stored


class CanonicalResearchResultsService:
    """Append one canonical context version from a reloaded successful execution."""

    def __init__(
        self,
        executions: _ExecutionReader,
        evidence: _EvidenceReader,
        snapshots: DecisionSnapshotRepository,
        conversations: ConversationRepository,
        integrations: InMemoryResultsIntegrationRepository
        | OperationalResultsIntegrationRepository
        | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._executions = executions
        self._evidence = evidence
        self._snapshots = snapshots
        self._conversations = conversations
        self._integrations = _require_integration_repository(executions, evidence, integrations)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = RLock()

    def integrate(
        self,
        *,
        execution_id: str,
        owner: ConversationOwner,
        conversation_id: str,
        decision_id: str,
    ) -> CanonicalIntegrationResult:
        """Reload the execution. Do not trust a caller-supplied success flag."""

        with self._lock:
            return self._integrate(
                execution_id=execution_id,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=decision_id,
            )

    def _integrate(
        self,
        *,
        execution_id: str,
        owner: ConversationOwner,
        conversation_id: str,
        decision_id: str,
    ) -> CanonicalIntegrationResult:
        try:
            execution = self._executions.get(execution_id)
        except PersistenceError:
            return _preserved(decision_id, "prior_decision_preserved")
        if execution is None:
            return _preserved(decision_id, "prior_decision_preserved")
        if execution.decision_id != decision_id:
            return _preserved(decision_id, "different_decision")
        refusal = _terminal_refusal(execution)
        if refusal is not None:
            return _preserved(decision_id, refusal)
        try:
            records = _resolve_production_evidence(self._evidence, execution)
        except FixtureEvidenceRejected:
            return _preserved(decision_id, "fixture_evidence_rejected")
        except MissingExecutionEvidence:
            return _preserved(decision_id, "evidence_unresolved")
        except PersistenceError:
            return _preserved(decision_id, "evidence_unresolved")
        latest = self._snapshots.get_latest_for_owner(decision_id, owner)
        if latest is None:
            probed = self._snapshots.get(decision_id, execution_context_version(execution))
            if probed is not None and not probed.owner.has_same_identity(owner):
                return _preserved(decision_id, "wrong_owner")
            return _preserved(decision_id, "wrong_owner")
        if not latest.owner.has_same_identity(owner):
            return _preserved(decision_id, "wrong_owner")
        conversation = self._conversations.get_for_owner(conversation_id, owner)
        if conversation is None or conversation.owner is None:
            return _preserved(decision_id, "wrong_owner")
        if not conversation.owner.has_same_identity(owner):
            return _preserved(decision_id, "wrong_owner")
        bound = conversation.decision_context
        if bound is not None and bound.decision_id != decision_id:
            return _preserved(decision_id, "different_decision")
        existing_integration = self._integrations.get(execution.execution_id)
        if existing_integration is not None and existing_integration.state in {
            "pending",
            "snapshot_written",
            "bound",
        }:
            return self._resume(
                existing_integration,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=decision_id,
            )
        if bound is None or bound.context_version != latest.context_version:
            return _preserved(decision_id, "prior_decision_preserved")
        mapping = _map_records(records, latest)
        if mapping == "outside":
            self._remember(
                execution,
                latest.context_version,
                records,
                "canonical_reevaluation_required",
                "canonical_reevaluation_required",
            )
            return _preserved(decision_id, "canonical_reevaluation_required", _ids(records))
        if mapping == "ambiguous":
            self._remember(
                execution,
                latest.context_version,
                records,
                "ambiguous_variant",
                "ambiguous_variant",
            )
            return _preserved(decision_id, "ambiguous_variant", _ids(records))
        return self._write_next_version(
            execution=execution,
            owner=owner,
            conversation_id=conversation_id,
            latest=latest,
            records=records,
            conversation_version=conversation.persistence_version,
        )

    def _write_next_version(
        self,
        *,
        execution: DurableAuthorizedExecution,
        owner: ConversationOwner,
        conversation_id: str,
        latest: CanonicalDecisionSnapshot,
        records: tuple[ResearchExecutionEvidence, ...],
        conversation_version: int,
    ) -> CanonicalIntegrationResult:
        existing = self._integrations.get(execution.execution_id)
        if existing is not None:
            return self._resume(
                existing,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=latest.decision_id,
            )
        intended = latest.context_version + 1
        pending = ResultsIntegrationRecord(
            execution_id=execution.execution_id,
            decision_id=latest.decision_id,
            context_version=intended,
            state="pending",
            evidence_ids=_ids(records),
            outcome="pending",
        )
        try:
            pending = self._integrations.insert(pending)
        except PersistenceConflictError:
            winner = self._integrations.get(execution.execution_id)
            if winner is None:
                return _preserved(latest.decision_id, "integration_conflict", _ids(records))
            return self._resume(
                winner,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=latest.decision_id,
            )
        snapshot = _next_snapshot(latest, records, now=self._clock())
        if snapshot.context_version != intended:
            raise RuntimeError("the server must assign the next context version")
        try:
            self._snapshots.add(snapshot)
        except DecisionSnapshotConflictError:
            stored = self._snapshots.get_for_owner(
                snapshot.decision_id,
                snapshot.context_version,
                owner,
            )
            if stored is None or not _matches_research_update(stored, snapshot):
                self._move(pending, state="integration_conflict", outcome="integration_conflict")
                return _preserved(
                    latest.decision_id,
                    "integration_conflict",
                    _ids(records),
                )
            snapshot = stored
        except (PersistenceError, DecisionSnapshotOwnershipError):
            self._move(pending, state="snapshot_failed", outcome="snapshot_persistence_failed")
            return _preserved(
                latest.decision_id,
                "snapshot_persistence_failed",
                _ids(records),
            )
        return self._promote_and_bind(
            pending,
            snapshot,
            owner=owner,
            conversation_id=conversation_id,
            conversation_version=conversation_version,
            records=records,
        )

    def _resume(
        self,
        record: ResultsIntegrationRecord,
        *,
        owner: ConversationOwner,
        conversation_id: str,
        decision_id: str,
    ) -> CanonicalIntegrationResult:
        if record.outcome in {
            "canonical_reevaluation_required",
            "ambiguous_variant",
            "fixture_evidence_rejected",
        }:
            return _preserved(decision_id, record.outcome, record.evidence_ids)  # type: ignore[arg-type]
        if record.state == "pending":
            return self._recover_pending(
                record,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=decision_id,
            )
        snapshot = self._snapshots.get_for_owner(decision_id, record.context_version, owner)
        if snapshot is None:
            return _preserved(decision_id, "snapshot_persistence_failed", record.evidence_ids)
        conversation = self._conversations.get_for_owner(conversation_id, owner)
        if conversation is None:
            return _preserved(decision_id, "conversation_binding_failed", record.evidence_ids)
        reference = snapshot.to_reference()
        if conversation.decision_context == reference or record.state == "bound":
            if conversation.decision_context != reference:
                rebound = self._bind(
                    conversation_id=conversation_id,
                    owner=owner,
                    snapshot=snapshot,
                    expected_version=conversation.persistence_version,
                )
                if rebound is None:
                    return _preserved(
                        decision_id,
                        "conversation_binding_failed",
                        record.evidence_ids,
                    )
            return CanonicalIntegrationResult(
                outcome="already_integrated",
                decision_id=decision_id,
                context_version=record.context_version,
                evidence_ids=record.evidence_ids,
                prior_decision_preserved=False,
                shopper_results_updated=True,
            )
        if record.state == "snapshot_written":
            rebound = self._bind(
                conversation_id=conversation_id,
                owner=owner,
                snapshot=snapshot,
                expected_version=conversation.persistence_version,
            )
            if rebound is None:
                return _preserved(
                    decision_id,
                    "conversation_binding_failed",
                    record.evidence_ids,
                )
            self._move(record, state="bound", outcome=record.outcome)
            return CanonicalIntegrationResult(
                outcome="already_integrated",
                decision_id=decision_id,
                context_version=record.context_version,
                evidence_ids=record.evidence_ids,
                prior_decision_preserved=False,
                shopper_results_updated=True,
            )
        return _preserved(decision_id, "integration_conflict", record.evidence_ids)

    def _recover_pending(
        self,
        record: ResultsIntegrationRecord,
        *,
        owner: ConversationOwner,
        conversation_id: str,
        decision_id: str,
    ) -> CanonicalIntegrationResult:
        """Continue a pending row after a crash instead of stranding it."""

        if record.decision_id != decision_id:
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        try:
            execution = self._executions.get(record.execution_id)
        except PersistenceError:
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        if execution is None or _terminal_refusal(execution) is not None:
            self._move(record, state="integration_conflict", outcome="integration_conflict")
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        try:
            records = _resolve_production_evidence(self._evidence, execution)
        except (FixtureEvidenceRejected, MissingExecutionEvidence, PersistenceError):
            self._move(record, state="integration_conflict", outcome="integration_conflict")
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        if record.evidence_ids != _ids(records):
            self._move(record, state="integration_conflict", outcome="integration_conflict")
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        latest = self._snapshots.get_latest_for_owner(decision_id, owner)
        stored = self._snapshots.get_for_owner(decision_id, record.context_version, owner)
        if stored is None:
            if latest is None or not latest.owner.has_same_identity(owner):
                return _preserved(decision_id, "wrong_owner", record.evidence_ids)
            if latest.context_version + 1 != record.context_version:
                self._move(record, state="integration_conflict", outcome="integration_conflict")
                return _preserved(decision_id, "integration_conflict", record.evidence_ids)
            conversation = self._conversations.get_for_owner(conversation_id, owner)
            if (
                conversation is None
                or not conversation.owner
                or not conversation.owner.has_same_identity(owner)
            ):
                return _preserved(decision_id, "wrong_owner", record.evidence_ids)
            return self._write_snapshot_from_pending(
                record,
                latest=latest,
                records=records,
                owner=owner,
                conversation_id=conversation_id,
                conversation_version=conversation.persistence_version,
            )
        previous = self._snapshots.get_for_owner(decision_id, record.context_version - 1, owner)
        expected = (
            None if previous is None else _next_snapshot(previous, records, now=stored.updated_at)
        )
        if previous is None or expected is None or not _matches_research_update(stored, expected):
            self._move(record, state="integration_conflict", outcome="integration_conflict")
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
        conversation = self._conversations.get_for_owner(conversation_id, owner)
        if conversation is None:
            return _preserved(decision_id, "conversation_binding_failed", record.evidence_ids)
        return self._promote_and_bind(
            record,
            stored,
            owner=owner,
            conversation_id=conversation_id,
            conversation_version=conversation.persistence_version,
            records=records,
        )

    def _write_snapshot_from_pending(
        self,
        pending: ResultsIntegrationRecord,
        *,
        latest: CanonicalDecisionSnapshot,
        records: tuple[ResearchExecutionEvidence, ...],
        owner: ConversationOwner,
        conversation_id: str,
        conversation_version: int,
    ) -> CanonicalIntegrationResult:
        snapshot = _next_snapshot(latest, records, now=self._clock())
        if snapshot.context_version != pending.context_version:
            raise RuntimeError("the server must assign the next context version")
        try:
            self._snapshots.add(snapshot)
        except DecisionSnapshotConflictError:
            stored = self._snapshots.get_for_owner(
                snapshot.decision_id,
                snapshot.context_version,
                owner,
            )
            if stored is None or not _matches_research_update(stored, snapshot):
                self._move(pending, state="integration_conflict", outcome="integration_conflict")
                return _preserved(latest.decision_id, "integration_conflict", _ids(records))
            snapshot = stored
        except (PersistenceError, DecisionSnapshotOwnershipError):
            self._move(pending, state="snapshot_failed", outcome="snapshot_persistence_failed")
            return _preserved(latest.decision_id, "snapshot_persistence_failed", _ids(records))
        return self._promote_and_bind(
            pending,
            snapshot,
            owner=owner,
            conversation_id=conversation_id,
            conversation_version=conversation_version,
            records=records,
        )

    def _promote_and_bind(
        self,
        pending: ResultsIntegrationRecord,
        snapshot: CanonicalDecisionSnapshot,
        *,
        owner: ConversationOwner,
        conversation_id: str,
        conversation_version: int,
        records: tuple[ResearchExecutionEvidence, ...],
    ) -> CanonicalIntegrationResult:
        written = self._move(
            pending,
            state="snapshot_written",
            outcome="canonical_results_updated",
        )
        if written is None:
            current = self._integrations.get(pending.execution_id)
            if current is None:
                return _preserved(snapshot.decision_id, "integration_conflict", _ids(records))
            return self._resume(
                current,
                owner=owner,
                conversation_id=conversation_id,
                decision_id=snapshot.decision_id,
            )
        conversation = self._conversations.get_for_owner(conversation_id, owner)
        expected_version = (
            conversation.persistence_version if conversation is not None else conversation_version
        )
        bound = self._bind(
            conversation_id=conversation_id,
            owner=owner,
            snapshot=snapshot,
            expected_version=expected_version,
        )
        if bound is None:
            conversation = self._conversations.get_for_owner(conversation_id, owner)
            reference = snapshot.to_reference()
            if conversation is None or conversation.decision_context != reference:
                return _preserved(
                    snapshot.decision_id,
                    "conversation_binding_failed",
                    _ids(records),
                )
        self._move(written, state="bound", outcome="canonical_results_updated")
        return CanonicalIntegrationResult(
            outcome="canonical_results_updated",
            decision_id=snapshot.decision_id,
            context_version=snapshot.context_version,
            evidence_ids=_ids(records),
            prior_decision_preserved=False,
            shopper_results_updated=True,
        )

    def _move(
        self,
        current: ResultsIntegrationRecord,
        *,
        state: str,
        outcome: str,
    ) -> ResultsIntegrationRecord | None:
        try:
            return self._integrations.transition(
                replace(current, state=state, outcome=outcome),
                expected_revision=current.revision,
            )
        except StaleIntegrationRevision:
            return None

    def _bind(
        self,
        *,
        conversation_id: str,
        owner: ConversationOwner,
        snapshot: CanonicalDecisionSnapshot,
        expected_version: int,
    ) -> object | None:
        binder = DecisionSnapshotBinder(self._snapshots, self._conversations)
        try:
            return binder.advance_after_verified_research(
                conversation_id,
                decision_id=snapshot.decision_id,
                context_version=snapshot.context_version,
                owner=owner,
                expected_conversation_version=expected_version,
            )
        except (
            ConversationContextDriftError,
            ConversationOwnershipError,
            ConversationVersionConflictError,
            DecisionSnapshotOwnershipError,
            PersistenceError,
            KeyError,
        ):
            return None

    def _remember(
        self,
        execution: DurableAuthorizedExecution,
        context_version: int,
        records: tuple[ResearchExecutionEvidence, ...],
        state: str,
        outcome: str,
    ) -> None:
        existing = self._integrations.get(execution.execution_id)
        record = ResultsIntegrationRecord(
            execution_id=execution.execution_id,
            decision_id=execution.decision_id,
            context_version=context_version,
            state=state,
            evidence_ids=_ids(records),
            outcome=outcome,
        )
        if existing is None:
            try:
                self._integrations.insert(record)
            except PersistenceConflictError:
                return
            return
        if existing.outcome == outcome:
            return


def execution_context_version(execution: DurableAuthorizedExecution) -> int:
    """The execution row does not store a client-supplied next version."""

    del execution
    return 1


def _terminal_refusal(execution: DurableAuthorizedExecution) -> IntegrationOutcome | None:
    if execution.state != "completed" or execution.outcome != "succeeded":
        return "prior_decision_preserved"
    trace = execution.trace
    if trace is None or not trace.steps or not trace.succeeded_sources:
        return "prior_decision_preserved"
    if any(step.attempt_status != "succeeded" for step in trace.steps):
        return "prior_decision_preserved"
    if trace.plan_id != execution.plan_id:
        return "prior_decision_preserved"
    if execution.observation_kind != "production":
        return "fixture_evidence_rejected"
    if execution.raw_response_persisted:
        return "prior_decision_preserved"
    if not execution.evidence_ids:
        return "evidence_unresolved"
    return None


def _resolve_production_evidence(
    evidence: _EvidenceReader,
    execution: DurableAuthorizedExecution,
) -> tuple[ResearchExecutionEvidence, ...]:
    trace = execution.trace
    if trace is None:
        raise MissingExecutionEvidence(execution.execution_id)
    trace_ids = tuple(
        dict.fromkeys(evidence_id for step in trace.steps for evidence_id in step.evidence_ids)
    )
    if trace_ids != execution.evidence_ids:
        raise MissingExecutionEvidence(execution.execution_id)
    records: list[ResearchExecutionEvidence] = []
    for evidence_id in trace_ids:
        record = evidence.require_production_evidence(evidence_id)
        if (
            record.execution_id != execution.execution_id
            or record.decision_id != execution.decision_id
            or record.plan_id != execution.plan_id
        ):
            raise MissingExecutionEvidence(evidence_id)
        if record.normalized_offer_digest in trace_ids:
            raise MissingExecutionEvidence(evidence_id)
        records.append(record)
    return tuple(records)


def _map_records(
    records: tuple[ResearchExecutionEvidence, ...],
    snapshot: CanonicalDecisionSnapshot,
) -> Literal["exact", "outside", "ambiguous"]:
    evaluated = {item.product_id: item.variant for item in snapshot.evaluated_products}
    saw_ambiguous = False
    for record in records:
        if record.product_id not in evaluated:
            return "outside"
        if record.variant_id != evaluated[record.product_id]:
            saw_ambiguous = True
        if record.capability == ResearchCapability.PRODUCT_DISCOVERY.value and (
            record.product_id not in evaluated
        ):
            return "outside"
    if saw_ambiguous:
        return "ambiguous"
    return "exact"


def _next_snapshot(
    previous: CanonicalDecisionSnapshot,
    records: tuple[ResearchExecutionEvidence, ...],
    *,
    now: datetime,
) -> CanonicalDecisionSnapshot:
    evidence = previous.evidence + tuple(_decision_evidence(record) for record in records)
    economics = _economics(previous, records)
    unknowns = tuple(dict.fromkeys((*previous.unknowns, *_UNKNOWN_COMPONENTS)))
    return replace(
        previous,
        context_version=previous.context_version + 1,
        evidence=evidence,
        offer_economics=economics,
        unknowns=unknowns,
        updated_at=now,
        data_classification="canonical_decision",
    )


def _decision_evidence(record: ResearchExecutionEvidence) -> DecisionEvidenceSnapshot:
    parts = [
        f"Observed listing price recorded in {record.currency} minor currency units.",
        f"Seller identity: {record.seller_identity}.",
    ]
    if record.availability:
        parts.append(f"Observed availability: {record.availability}.")
    fact = " ".join(parts)
    return DecisionEvidenceSnapshot(
        evidence_id=record.evidence_id,
        product_id=record.product_id,
        topic="observed_listing_price",
        fact=fact,
        source=record.source,
        captured_at=record.observed_at,
        freshness=_freshness(record),
        provenance_sha256=stable_sha256(record._identity_payload()),  # noqa: SLF001
    )


def _freshness(record: ResearchExecutionEvidence) -> Literal["fresh", "stale", "unknown"]:
    """Query-time freshness only. Fixture evidence stays unknown."""

    if record.test_fixture or record.observation_kind != "production":
        return "unknown"
    technical = evaluate_freshness(
        source_mode=record.source_mode,
        observed_at=record.observed_at,
        source_timestamp=None,
        ingested_at=record.observed_at,
        now=record.observed_at,
        connector_healthy=None,
        simulated=False,
    )
    if technical.status is FreshnessStatus.FRESH and technical.is_current_live_price:
        return "fresh"
    if technical.status is FreshnessStatus.STALE:
        return "stale"
    return "unknown"


def _economics(
    previous: CanonicalDecisionSnapshot,
    records: tuple[ResearchExecutionEvidence, ...],
) -> tuple[CanonicalOfferEconomics, ...]:
    by_product = {item.product_id: item for item in previous.offer_economics}
    for record in records:
        if record.capability != _PRICE:
            continue
        existing = by_product.get(record.product_id)
        if existing is None:
            continue
        by_product[record.product_id] = _price_economics(previous=existing, record=record)
    return tuple(by_product[item.product_id] for item in previous.offer_economics)


def _price_economics(
    *,
    previous: CanonicalOfferEconomics,
    record: ResearchExecutionEvidence,
) -> CanonicalOfferEconomics:
    currency = record.currency
    listing = CanonicalMoneyLine(
        kind="listing",
        amount_minor=record.amount_minor,
        currency=currency,
        status="verified",
        applied=True,
        evidence_id=record.evidence_id,
        label="observed listing price",
    )
    shipping = _preserved_or_unknown(previous.shipping, "shipping", currency)
    taxes = _preserved_or_unknown(previous.taxes, "tax", currency)
    voucher = _preserved_or_unknown(previous.voucher, "voucher", currency)
    imports = _preserved_or_unknown(previous.import_charges, "import", currency)
    evidence_ids = previous.evidence_ids
    if record.evidence_id not in evidence_ids:
        evidence_ids = (*evidence_ids, record.evidence_id)
    return CanonicalOfferEconomics(
        offer_id=previous.offer_id,
        product_id=record.product_id,
        currency=currency,
        listing=listing,
        shipping=shipping,
        taxes=taxes,
        price_state="price_before_shipping",
        dominant_amount_minor=record.amount_minor,
        merchant=previous.merchant,
        marketplace=previous.marketplace,
        seller_id=previous.seller_id,
        voucher=voucher,
        import_charges=imports,
        delivery=previous.delivery,
        international=previous.international,
        unknowns=tuple(dict.fromkeys((*previous.unknowns, *_UNKNOWN_COMPONENTS))),
        evidence_ids=evidence_ids,
        provenance_source=record.source,
        checked_at=record.observed_at,
        freshness=_freshness(record),
    )


def _preserved_or_unknown(
    previous: CanonicalMoneyLine | None,
    kind: str,
    currency: str,
) -> CanonicalMoneyLine:
    if previous is None or previous.status == "unknown" or previous.amount_minor is None:
        return CanonicalMoneyLine(
            kind=kind,  # type: ignore[arg-type]
            amount_minor=None,
            currency=currency,
            status="unknown",
            applied=False,
        )
    if previous.currency != currency:
        return CanonicalMoneyLine(
            kind=kind,  # type: ignore[arg-type]
            amount_minor=None,
            currency=currency,
            status="unknown",
            applied=False,
        )
    return previous


def _same_research_version(
    stored: CanonicalDecisionSnapshot,
    expected: CanonicalDecisionSnapshot,
) -> bool:
    return (
        stored.decision_id == expected.decision_id
        and stored.context_version == expected.context_version
        and stored.owner.has_same_identity(expected.owner)
        and stored.evidence_ids == expected.evidence_ids
        and stored.canonical_piqscore_set_sha256 == expected.canonical_piqscore_set_sha256
        and stored.recommendation.snapshot_sha256 == expected.recommendation.snapshot_sha256
        and stored.recommendation.best_piq_product_id == expected.recommendation.best_piq_product_id
    )


def _matches_research_update(
    stored: CanonicalDecisionSnapshot,
    expected: CanonicalDecisionSnapshot,
) -> bool:
    if not _same_research_version(stored, expected):
        return False
    if len(stored.offer_economics) != len(expected.offer_economics):
        return False
    for left, right in zip(stored.offer_economics, expected.offer_economics, strict=True):
        if left.product_id != right.product_id:
            return False
        if left.listing.amount_minor != right.listing.amount_minor:
            return False
        if left.international != right.international or left.delivery != right.delivery:
            return False
    return True


def _require_integration_repository(
    executions: object,
    evidence: object,
    integrations: InMemoryResultsIntegrationRepository
    | OperationalResultsIntegrationRepository
    | None,
) -> InMemoryResultsIntegrationRepository | OperationalResultsIntegrationRepository:
    durable = bool(getattr(executions, "persists_across_process_restart", False)) or bool(
        getattr(evidence, "persists_across_process_restart", False)
    )
    if integrations is None:
        if durable:
            raise ValueError(
                "durable research repositories require OperationalResultsIntegrationRepository"
            )
        return InMemoryResultsIntegrationRepository()
    if durable and not getattr(integrations, "persists_across_process_restart", False):
        raise ValueError(
            "durable research repositories require OperationalResultsIntegrationRepository"
        )
    return integrations


def _ids(records: tuple[ResearchExecutionEvidence, ...]) -> tuple[str, ...]:
    return tuple(record.evidence_id for record in records)


def _preserved(
    decision_id: str,
    outcome: IntegrationOutcome,
    evidence_ids: tuple[str, ...] = (),
) -> CanonicalIntegrationResult:
    return CanonicalIntegrationResult(
        outcome=outcome,
        decision_id=decision_id,
        context_version=None,
        evidence_ids=evidence_ids,
        prior_decision_preserved=True,
        shopper_results_updated=False,
    )
