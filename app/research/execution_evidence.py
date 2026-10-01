"""Durable normalized research-outcome evidence.

``normalized_offer_digests`` on an execution row are integrity digests. They
are not evidence ids. An id in this module resolves to one stored record in
``research.execution_evidence`` on the existing ``operational_entities`` table.
No new SQL table is added.

Fake-transport output is stored with ``test_fixture=True``. That record cannot
use ``SourceMode.LIVE``, cannot activate a public market, and cannot be read
back as production live evidence. Raw Shopify JSON, request bodies, claim
capabilities, and probe capabilities are not fields on this record.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.marketplace_data import SourceMode
from app.domain.entities.research_execution import (
    ResearchExecutionTrace,
    ResearchExecutionTraceStep,
    require_durable_evidence_reference,
)
from app.infrastructure.persistence.errors import PersistenceConflictError, PersistenceError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import RESEARCH_EXECUTION_EVIDENCE
from app.research.authorized_execution_repository import (
    AuthorizedExecutionRevisionConflict,
    DurableAuthorizedExecution,
    InMemoryAuthorizedExecutionRepository,
    OperationalAuthorizedExecutionRepository,
)
from app.research.digest import stable_sha256
from app.research.shopify_global_catalog_transport import ProductionTransportAuthority

EVIDENCE_ID_PREFIX = "research-exec-evidence:"
ObservationKind = Literal["synthetic", "production"]
_EXECUTION_REPOSITORY = (
    InMemoryAuthorizedExecutionRepository | OperationalAuthorizedExecutionRepository
)


class EvidenceIdentityConflict(PersistenceError):
    """The same evidence id was presented with different normalized facts."""

    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        super().__init__(f"research execution evidence conflict for {evidence_id}")


class MissingExecutionEvidence(PersistenceError):
    """A trace evidence id does not resolve to a stored record."""

    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        super().__init__(f"research execution evidence was not found: {evidence_id}")


class FixtureEvidenceRejected(PersistenceError):
    """Fixture or synthetic evidence cannot pass the production live gate."""

    def __init__(self, evidence_id: str, reason: str) -> None:
        self.evidence_id = evidence_id
        self.reason = reason
        super().__init__(f"{evidence_id} rejected as live evidence: {reason}")


@dataclass(frozen=True, slots=True)
class NormalizedOfferFact:
    """Normalized adapter fact. Not a raw Shopify response and not an evidence id."""

    product_id: str
    variant_id: str | None
    seller_identity: str
    amount_minor: int
    currency: str
    availability: str | None
    observed_at: datetime
    normalized_offer_digest: str
    observation_kind: str
    source_mode: str
    provider_id: str
    capability: str
    market: str
    source: str


@dataclass(frozen=True, slots=True)
class ResearchExecutionEvidence:
    """One resolvable normalized outcome. Not a Results snapshot."""

    evidence_id: str
    execution_id: str
    decision_id: str
    plan_id: str
    provider_id: str
    capability: str
    market: str
    source: str
    product_id: str
    variant_id: str | None
    seller_identity: str
    amount_minor: int
    currency: str
    availability: str | None
    observed_at: datetime
    normalized_offer_digest: str
    observation_kind: ObservationKind
    test_fixture: bool
    source_mode: SourceMode
    raw_response_persisted: bool
    created_at: datetime
    launch_evidence: bool = False
    activates_public_market: bool = False

    def __post_init__(self) -> None:
        require_durable_evidence_reference(self.evidence_id)
        if not self.evidence_id.startswith(EVIDENCE_ID_PREFIX):
            raise ValueError("evidence_id must be a research execution evidence reference")
        if self.evidence_id != research_execution_evidence_id(self._identity_payload()):
            raise ValueError("evidence_id does not match the normalized evidence digest")
        if self.raw_response_persisted:
            raise ValueError("raw Shopify responses must not be persisted")
        if self.launch_evidence:
            raise ValueError("research execution evidence is not launch evidence")
        if self.activates_public_market:
            raise ValueError("research execution evidence cannot activate a public market")
        if self.observation_kind not in {"synthetic", "production"}:
            raise ValueError("observation_kind must be synthetic or production")
        if self.test_fixture and self.source_mode is SourceMode.LIVE:
            raise ValueError("fixture evidence cannot be represented as SourceMode.LIVE")
        if self.test_fixture and self.observation_kind != "synthetic":
            raise ValueError("fixture evidence must stay a synthetic observation")
        if not self.test_fixture and self.observation_kind != "production":
            raise ValueError("production evidence requires a production observation")
        if not self.test_fixture and self.source_mode is not SourceMode.LIVE:
            raise ValueError("production evidence uses the live source mode")
        if self.observed_at.utcoffset() is None or self.created_at.utcoffset() is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        if isinstance(self.amount_minor, bool) or self.amount_minor < 0:
            raise ValueError("amount_minor must be a non-negative integer")
        if len(self.normalized_offer_digest) != 64:
            raise ValueError("normalized_offer_digest must stay a digest")
        if self.normalized_offer_digest == self.evidence_id:
            raise ValueError("a normalized offer digest is not an evidence id")

    def _identity_payload(self) -> dict[str, object]:
        return {
            "execution_id": self.execution_id,
            "decision_id": self.decision_id,
            "plan_id": self.plan_id,
            "provider_id": self.provider_id,
            "capability": self.capability,
            "market": self.market,
            "source": self.source,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "seller_identity": self.seller_identity,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "availability": self.availability,
            "observed_at": self.observed_at.isoformat(),
            "normalized_offer_digest": self.normalized_offer_digest,
            "observation_kind": self.observation_kind,
            "test_fixture": self.test_fixture,
            "source_mode": self.source_mode.value,
        }


def research_execution_evidence_id(identity: dict[str, object]) -> str:
    """Deterministic id. The same normalized facts resolve to the same record."""

    digest = stable_sha256({"kind": "research_execution_evidence_v1", **identity})
    return f"{EVIDENCE_ID_PREFIX}{digest}"


def build_research_execution_evidence(
    *,
    execution_id: str,
    decision_id: str,
    plan_id: str,
    provider_id: str,
    capability: str,
    market: str,
    source: str,
    product_id: str,
    variant_id: str | None,
    seller_identity: str,
    amount_minor: int,
    currency: str,
    availability: str | None,
    observed_at: datetime,
    normalized_offer_digest: str,
    observation_kind: ObservationKind,
    test_fixture: bool,
    created_at: datetime,
) -> ResearchExecutionEvidence:
    """Build one evidence record. Fixture input cannot be labeled live."""

    source_mode = SourceMode.FIXTURE if test_fixture else SourceMode.LIVE
    identity = {
        "execution_id": execution_id,
        "decision_id": decision_id,
        "plan_id": plan_id,
        "provider_id": provider_id,
        "capability": capability,
        "market": market,
        "source": source,
        "product_id": product_id,
        "variant_id": variant_id,
        "seller_identity": seller_identity,
        "amount_minor": amount_minor,
        "currency": currency,
        "availability": availability,
        "observed_at": observed_at.isoformat(),
        "normalized_offer_digest": normalized_offer_digest,
        "observation_kind": observation_kind,
        "test_fixture": test_fixture,
        "source_mode": source_mode.value,
    }
    return ResearchExecutionEvidence(
        evidence_id=research_execution_evidence_id(identity),
        execution_id=execution_id,
        decision_id=decision_id,
        plan_id=plan_id,
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        product_id=product_id,
        variant_id=variant_id,
        seller_identity=seller_identity,
        amount_minor=amount_minor,
        currency=currency,
        availability=availability,
        observed_at=observed_at,
        normalized_offer_digest=normalized_offer_digest,
        observation_kind=observation_kind,
        test_fixture=test_fixture,
        source_mode=source_mode,
        raw_response_persisted=False,
        created_at=created_at,
    )


@dataclass(frozen=True, slots=True)
class VerifiedLiveOfferExecution:
    """Server proof that facts came from a production-authority Shopify success.

    A browser request cannot supply this object. The Shopify adapter creates it
    only after ``ProductionShopifyTransportPermit``, a server-issued production
    transport authority, and a successful terminal outcome. The authority
    marker stays in memory and is not a persisted evidence field. Synthetic
    and harness adapter output cannot construct it.
    """

    execution_id: str
    decision_id: str
    plan_id: str
    permit_marker: Literal["production_shopify_transport"]
    transport_authority: ProductionTransportAuthority
    facts: tuple[NormalizedOfferFact, ...]

    def __post_init__(self) -> None:
        if self.permit_marker != "production_shopify_transport":
            raise ValueError("verified live evidence requires the production transport permit")
        if type(self.transport_authority) is not ProductionTransportAuthority:
            raise ValueError("verified live evidence requires production transport authority")
        if not self.transport_authority.proves_production_transport():
            raise ValueError("verified live evidence requires production transport authority")
        if not self.execution_id or not self.decision_id or not self.plan_id:
            raise ValueError("verified live evidence requires execution, decision, and plan pins")
        if not self.facts:
            raise ValueError("verified live evidence requires normalized production facts")
        for fact in self.facts:
            if fact.observation_kind != "production" or fact.source_mode != SourceMode.LIVE.value:
                raise ValueError("verified live facts must be production observations")


def evidence_from_verified_live_offer_fact(
    verification: VerifiedLiveOfferExecution,
    fact: NormalizedOfferFact,
    *,
    created_at: datetime,
) -> ResearchExecutionEvidence:
    """Convert one fact that the production adapter already verified.

    The synthetic converter cannot call this. Arbitrary caller facts that are
    not on the verified execution are rejected.
    """

    if type(verification.transport_authority) is not ProductionTransportAuthority:
        raise ValueError("live evidence requires production transport authority")
    if not verification.transport_authority.proves_production_transport():
        raise ValueError("live evidence requires production transport authority")
    if fact not in verification.facts:
        raise ValueError("live evidence requires a fact from the verified production execution")
    if fact.observation_kind != "production" or fact.source_mode != SourceMode.LIVE.value:
        raise ValueError("verified live evidence cannot be a fixture observation")
    return build_research_execution_evidence(
        execution_id=verification.execution_id,
        decision_id=verification.decision_id,
        plan_id=verification.plan_id,
        provider_id=fact.provider_id,
        capability=fact.capability,
        market=fact.market,
        source=fact.source,
        product_id=fact.product_id,
        variant_id=fact.variant_id,
        seller_identity=fact.seller_identity,
        amount_minor=fact.amount_minor,
        currency=fact.currency,
        availability=fact.availability,
        observed_at=fact.observed_at,
        normalized_offer_digest=fact.normalized_offer_digest,
        observation_kind="production",
        test_fixture=False,
        created_at=created_at,
    )


def evidence_from_adapter_fact(
    fact: NormalizedOfferFact,
    *,
    execution_id: str,
    decision_id: str,
    plan_id: str,
    created_at: datetime,
) -> ResearchExecutionEvidence:
    """Adapter facts are synthetic fixtures. They cannot become live evidence."""

    if fact.observation_kind in {"live", "production"} or fact.source_mode == SourceMode.LIVE.value:
        raise ValueError("adapter output cannot be relabeled as live evidence")
    return build_research_execution_evidence(
        execution_id=execution_id,
        decision_id=decision_id,
        plan_id=plan_id,
        provider_id=fact.provider_id,
        capability=fact.capability,
        market=fact.market,
        source=fact.source,
        product_id=fact.product_id,
        variant_id=fact.variant_id,
        seller_identity=fact.seller_identity,
        amount_minor=fact.amount_minor,
        currency=fact.currency,
        availability=fact.availability,
        observed_at=fact.observed_at,
        normalized_offer_digest=fact.normalized_offer_digest,
        observation_kind="synthetic",
        test_fixture=True,
        created_at=created_at,
    )


def _same_facts(left: ResearchExecutionEvidence, right: ResearchExecutionEvidence) -> bool:
    return left._identity_payload() == right._identity_payload()  # noqa: SLF001


class InMemoryResearchExecutionEvidenceRepository:
    """Process-local evidence store. A new instance does not see other rows."""

    persists_across_process_restart = False

    def __init__(self) -> None:
        self._rows: dict[str, ResearchExecutionEvidence] = {}

    def get(self, evidence_id: str) -> ResearchExecutionEvidence | None:
        return self._rows.get(evidence_id)

    def save(self, record: ResearchExecutionEvidence) -> ResearchExecutionEvidence:
        existing = self._rows.get(record.evidence_id)
        if existing is not None:
            if not _same_facts(existing, record):
                raise EvidenceIdentityConflict(record.evidence_id)
            return existing
        self._rows[record.evidence_id] = record
        return record

    def require_production_evidence(self, evidence_id: str) -> ResearchExecutionEvidence:
        record = self.get(evidence_id)
        if record is None:
            raise MissingExecutionEvidence(evidence_id)
        _reject_unless_production(record)
        return record


class OperationalResearchExecutionEvidenceRepository(SessionBound):
    """``research.execution_evidence`` rows. No schema migration."""

    persists_across_process_restart = True

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
    ) -> None:
        super().__init__(session_factory=session_factory, session=session)

    def get(self, evidence_id: str) -> ResearchExecutionEvidence | None:
        with self._ops() as ops:
            return ops.get(RESEARCH_EXECUTION_EVIDENCE, evidence_id, ResearchExecutionEvidence)

    def save(self, record: ResearchExecutionEvidence) -> ResearchExecutionEvidence:
        existing = self.get(record.evidence_id)
        if existing is not None:
            if not _same_facts(existing, record):
                raise EvidenceIdentityConflict(record.evidence_id)
            return existing
        try:
            with self._ops() as ops:
                ops.insert_versioned(
                    RESEARCH_EXECUTION_EVIDENCE,
                    record.evidence_id,
                    record,
                    version=1,
                )
        except PersistenceConflictError:
            winner = self.get(record.evidence_id)
            if winner is None:
                raise
            if not _same_facts(winner, record):
                raise EvidenceIdentityConflict(record.evidence_id) from None
            return winner
        return record

    def require_production_evidence(self, evidence_id: str) -> ResearchExecutionEvidence:
        record = self.get(evidence_id)
        if record is None:
            raise MissingExecutionEvidence(evidence_id)
        _reject_unless_production(record)
        return record


def _reject_unless_production(record: ResearchExecutionEvidence) -> None:
    if record.test_fixture:
        raise FixtureEvidenceRejected(record.evidence_id, "test_fixture")
    if record.observation_kind != "production":
        raise FixtureEvidenceRejected(record.evidence_id, "observation_not_production")
    if record.source_mode is not SourceMode.LIVE:
        raise FixtureEvidenceRejected(record.evidence_id, "source_mode_not_live")
    if record.launch_evidence or record.activates_public_market:
        raise FixtureEvidenceRejected(record.evidence_id, "launch_or_market_activation")
    if record.raw_response_persisted:
        raise FixtureEvidenceRejected(record.evidence_id, "raw_response")


@dataclass(frozen=True, slots=True)
class TraceEvidenceAttachment:
    """Result of a compare-and-swap that only adds resolvable evidence ids."""

    attached: bool
    evidence_ids: tuple[str, ...]
    reason: str


def attach_execution_evidence_references(
    executions: _EXECUTION_REPOSITORY,
    evidence: InMemoryResearchExecutionEvidenceRepository
    | OperationalResearchExecutionEvidenceRepository,
    execution_id: str,
    evidence_ids: tuple[str, ...],
) -> TraceEvidenceAttachment:
    """Point a successful terminal trace at evidence that already exists.

    A lost compare-and-swap reloads the winner. It does not rewrite the
    terminal outcome or invent ids.
    """

    current = executions.get(execution_id)
    if current is None or current.trace is None:
        return TraceEvidenceAttachment(False, (), "execution_not_terminal")
    if current.state != "completed" or current.outcome != "succeeded":
        return TraceEvidenceAttachment(False, current.evidence_ids, "execution_not_successful")
    if not evidence_ids:
        return TraceEvidenceAttachment(False, current.evidence_ids, "evidence_ids_empty")
    for evidence_id in evidence_ids:
        if evidence.get(evidence_id) is None:
            return TraceEvidenceAttachment(False, current.evidence_ids, "evidence_unresolved")
    if current.evidence_ids == evidence_ids:
        return TraceEvidenceAttachment(True, current.evidence_ids, "already_attached")
    if current.evidence_ids:
        return TraceEvidenceAttachment(False, current.evidence_ids, "evidence_reference_conflict")
    try:
        replacement = _with_evidence_ids(current, evidence_ids)
        executions.cas_replace(replacement, expected_revision=current.revision)
    except AuthorizedExecutionRevisionConflict:
        winner = executions.get(execution_id)
        if winner is not None and winner.evidence_ids == evidence_ids:
            return TraceEvidenceAttachment(True, evidence_ids, "already_attached")
        kept = () if winner is None else winner.evidence_ids
        return TraceEvidenceAttachment(False, kept, "trace_reference_race_preserved")
    return TraceEvidenceAttachment(True, evidence_ids, "attached")


def _with_evidence_ids(
    current: DurableAuthorizedExecution,
    evidence_ids: tuple[str, ...],
) -> DurableAuthorizedExecution:
    trace = current.trace
    if trace is None:
        raise ValueError("a terminal execution requires a trace")
    steps = tuple(_step_with_evidence(step, evidence_ids) for step in trace.steps)
    updated_trace = ResearchExecutionTrace(
        plan_id=trace.plan_id,
        steps=steps,
        attempted_sources=trace.attempted_sources,
        succeeded_sources=trace.succeeded_sources,
        failed_sources=trace.failed_sources,
        timed_out_sources=trace.timed_out_sources,
        evaluated_offer_count=trace.evaluated_offer_count,
    )
    return replace(current, evidence_ids=evidence_ids, trace=updated_trace)


def _step_with_evidence(
    step: ResearchExecutionTraceStep,
    evidence_ids: tuple[str, ...],
) -> ResearchExecutionTraceStep:
    if step.attempt_status != "succeeded":
        return step
    return replace(step, evidence_ids=evidence_ids)
