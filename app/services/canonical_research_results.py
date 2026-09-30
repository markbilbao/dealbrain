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


@dataclass(frozen=True, slots=True)
class ResultsIntegrationRecord:
    """One execution may create at most one next canonical version."""

    execution_id: str
    decision_id: str
    context_version: int
    state: str
    evidence_ids: tuple[str, ...]
    outcome: str


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
    """Idempotency lock for one process. The execution id is the key."""

    def __init__(self) -> None:
        self._rows: dict[str, ResultsIntegrationRecord] = {}

    def get(self, execution_id: str) -> ResultsIntegrationRecord | None:
        return self._rows.get(execution_id)

    def insert(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        existing = self._rows.get(record.execution_id)
        if existing is not None:
            raise PersistenceConflictError(record.execution_id)
        self._rows[record.execution_id] = record
        return record

    def replace(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        if record.execution_id not in self._rows:
            raise PersistenceError(f"missing integration {record.execution_id}")
        self._rows[record.execution_id] = record
        return record


class OperationalResultsIntegrationRepository(SessionBound):
    """``research.execution_results_integration`` on the existing operational table."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
    ) -> None:
        super().__init__(session_factory=session_factory, session=session)

    def get(self, execution_id: str) -> ResultsIntegrationRecord | None:
        with self._ops() as ops:
            return ops.get(
                RESEARCH_RESULTS_INTEGRATION,
                execution_id,
                ResultsIntegrationRecord,
            )

    def insert(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        try:
            with self._ops() as ops:
                ops.insert_versioned(
                    RESEARCH_RESULTS_INTEGRATION,
                    record.execution_id,
                    record,
                    version=1,
                )
        except PersistenceConflictError as exc:
            raise PersistenceConflictError(record.execution_id) from exc
        return record

    def replace(self, record: ResultsIntegrationRecord) -> ResultsIntegrationRecord:
        with self._ops() as ops:
            ops.upsert(
                RESEARCH_RESULTS_INTEGRATION,
                record.execution_id,
                record,
            )
        return record


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
        self._integrations = integrations or InMemoryResultsIntegrationRepository()
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
            self._integrations.insert(pending)
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
            if stored is None or not _same_research_version(stored, snapshot):
                self._integrations.replace(
                    replace(pending, state="snapshot_failed", outcome="snapshot_persistence_failed")
                )
                return _preserved(
                    latest.decision_id,
                    "integration_conflict",
                    _ids(records),
                )
            snapshot = stored
        except (PersistenceError, DecisionSnapshotOwnershipError):
            self._integrations.replace(
                replace(pending, state="snapshot_failed", outcome="snapshot_persistence_failed")
            )
            return _preserved(
                latest.decision_id,
                "snapshot_persistence_failed",
                _ids(records),
            )
        written = replace(pending, state="snapshot_written", outcome="canonical_results_updated")
        self._integrations.replace(written)
        bound = self._bind(
            conversation_id=conversation_id,
            owner=owner,
            snapshot=snapshot,
            expected_version=conversation_version,
        )
        if bound is None:
            return _preserved(
                latest.decision_id,
                "conversation_binding_failed",
                _ids(records),
            )
        self._integrations.replace(replace(written, state="bound"))
        return CanonicalIntegrationResult(
            outcome="canonical_results_updated",
            decision_id=snapshot.decision_id,
            context_version=snapshot.context_version,
            evidence_ids=_ids(records),
            prior_decision_preserved=False,
            shopper_results_updated=True,
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
            return _preserved(decision_id, "integration_conflict", record.evidence_ids)
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
            self._integrations.replace(replace(record, state="bound"))
            return CanonicalIntegrationResult(
                outcome="already_integrated",
                decision_id=decision_id,
                context_version=record.context_version,
                evidence_ids=record.evidence_ids,
                prior_decision_preserved=False,
                shopper_results_updated=True,
            )
        return _preserved(decision_id, "integration_conflict", record.evidence_ids)

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
        dict.fromkeys(
            evidence_id for step in trace.steps for evidence_id in step.evidence_ids
        )
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
        f"Observed listing price {record.amount_minor} {record.currency}.",
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
        by_product[record.product_id] = _price_economics(
            previous=by_product.get(record.product_id),
            record=record,
        )
    ordered: list[CanonicalOfferEconomics] = []
    seen: set[str] = set()
    for item in previous.offer_economics:
        ordered.append(by_product[item.product_id])
        seen.add(item.product_id)
    for product_id, item in by_product.items():
        if product_id not in seen:
            ordered.append(item)
    return tuple(ordered)


def _price_economics(
    *,
    previous: CanonicalOfferEconomics | None,
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
    shipping = _preserved_or_unknown(
        None if previous is None else previous.shipping,
        "shipping",
        currency,
    )
    taxes = _preserved_or_unknown(None if previous is None else previous.taxes, "tax", currency)
    voucher = _preserved_or_unknown(
        None if previous is None else previous.voucher,
        "voucher",
        currency,
    )
    imports = _preserved_or_unknown(
        None if previous is None else previous.import_charges,
        "import",
        currency,
    )
    evidence_ids = () if previous is None else previous.evidence_ids
    if record.evidence_id not in evidence_ids:
        evidence_ids = (*evidence_ids, record.evidence_id)
    return CanonicalOfferEconomics(
        offer_id=(
            previous.offer_id
            if previous is not None
            else f"research-offer:{record.product_id}"[:128]
        ),
        product_id=record.product_id,
        currency=currency,
        listing=listing,
        shipping=shipping,
        taxes=taxes,
        price_state="price_before_shipping",
        dominant_amount_minor=record.amount_minor,
        merchant=record.seller_identity[:128],
        marketplace=record.source[:128],
        seller_id=record.seller_identity[:128],
        voucher=voucher,
        import_charges=imports,
        delivery=None if previous is None else previous.delivery,
        international=False if previous is None else previous.international,
        unknowns=_UNKNOWN_COMPONENTS,
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
