"""Sprint 38 B2 durable evidence and canonical Results integration."""

from __future__ import annotations

import socket
import urllib.request
from dataclasses import fields, replace
from datetime import UTC, datetime
from threading import Thread

import pytest
from app.domain.entities.marketplace_data import SourceMode
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchExecutionTrace,
    ResearchExecutionTraceStep,
)
from app.domain.exceptions import ConversationContextDriftError
from app.infrastructure.persistence.errors import PersistenceError
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.market.support import production_certified_shopping_markets
from app.research.authorized_execution_repository import (
    AuthorizedExecutionRevisionConflict,
    DurableAuthorizedExecution,
    InMemoryAuthorizedExecutionRepository,
)
from app.research.execution_evidence import (
    FixtureEvidenceRejected,
    InMemoryResearchExecutionEvidenceRepository,
    NormalizedOfferFact,
    ResearchExecutionEvidence,
    attach_execution_evidence_references,
    build_research_execution_evidence,
    evidence_from_adapter_fact,
    research_execution_evidence_id,
)
from app.research.shopify_global_catalog_certification_evidence import SHOPIFY_GLOBAL_CATALOG_SOURCE
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.shopify_global_catalog_provider import SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
)
from app.services.canonical_research_results import CanonicalResearchResultsService
from app.services.research_execution import authorized_execution_id

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    BOSE_ID,
    DECISION_ID,
    SENN_ID,
    SONY_ID,
    START,
    _base_snapshot,
    _owner,
)

_DIGEST = "ab" * 32
_OTHER_DIGEST = "cd" * 32
_PLAN = "plan-sprint38-b2"
_AUTH_KEY = "research-auth:" + ("12" * 32)
_PRICE = ResearchCapability.CURRENT_PRICING
_SOURCE = SHOPIFY_GLOBAL_CATALOG_SOURCE


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("execution-evidence tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(urllib.request, "urlopen", _blocked)


def _evidence(
    *,
    execution_id: str,
    product_id: str = SONY_ID,
    variant_id: str | None = "black",
    amount_minor: int = 18990,
    test_fixture: bool = False,
    observation_kind: str = "production",
    capability: ResearchCapability = _PRICE,
    availability: str | None = "in_stock",
    digest: str = _DIGEST,
    seller: str = "North Audio",
    currency: str = "USD",
):
    return build_research_execution_evidence(
        execution_id=execution_id,
        decision_id=DECISION_ID,
        plan_id=_PLAN,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        capability=capability.value,
        market="PH",
        source=_SOURCE,
        product_id=product_id,
        variant_id=variant_id,
        seller_identity=seller,
        amount_minor=amount_minor,
        currency=currency,
        availability=availability,
        observed_at=START,
        normalized_offer_digest=digest,
        observation_kind=observation_kind,  # type: ignore[arg-type]
        test_fixture=test_fixture,
        created_at=START,
    )


def _trace(
    evidence_ids: tuple[str, ...],
    *,
    status: str = "succeeded",
    error_category: str | None = None,
    offers: int = 1,
) -> ResearchExecutionTrace:
    succeeded = status == "succeeded"
    step = ResearchExecutionTraceStep(
        plan_id=_PLAN,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        requested_capability=_PRICE,
        market="PH",
        source=_SOURCE,
        attempted=True,
        attempt_status=status,  # type: ignore[arg-type]
        evidence_ids=evidence_ids if succeeded else (),
        started_at=START,
        finished_at=START,
        error_category=None if succeeded else error_category,
        evaluated_offer_count=offers if succeeded else 0,
        freshness_checked_at=START if succeeded else None,
    )
    return ResearchExecutionTrace(
        plan_id=_PLAN,
        steps=(step,),
        attempted_sources=(_SOURCE,),
        succeeded_sources=(_SOURCE,) if succeeded else (),
        failed_sources=(_SOURCE,) if status == "failed" else (),
        timed_out_sources=(_SOURCE,) if status == "timed_out" else (),
        evaluated_offer_count=offers if succeeded else 0,
    )


def _install_execution(
    executions: InMemoryAuthorizedExecutionRepository,
    *,
    execution_id: str,
    state: str,
    outcome: str,
    error_category: str | None,
    evidence_ids: tuple[str, ...] = (),
    observation_kind: str | None = "production",
    decision_id: str = DECISION_ID,
    digests: tuple[str, ...] = (_DIGEST,),
    amounts: tuple[int, ...] = (18990,),
    currencies: tuple[str, ...] = ("USD",),
) -> DurableAuthorizedExecution:
    prepared = executions.bind(
        authorization_idempotency_key=_AUTH_KEY,
        authorization_id="auth-b2",
        authorization_version=1,
        decision_id=decision_id,
        plan_id=_PLAN,
        now=START,
    )
    success = state == "completed"
    trace = _trace(
        evidence_ids,
        status="succeeded" if success else ("timed_out" if outcome == "timed_out" else state),
        error_category=error_category,
        offers=1 if success else 0,
    )
    if state == "outcome_unknown":
        trace = _trace((), status="outcome_unknown", error_category="outcome_unknown", offers=0)
        observation_kind = None
        digests = ()
        amounts = ()
        currencies = ()
    elif state != "completed" and observation_kind == "production":
        observation_kind = "synthetic"
    completed = replace(
        prepared,
        state=state,  # type: ignore[arg-type]
        updated_at=START,
        attempt_started_at=START,
        finished_at=START,
        attempted_provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        attempted_capability=_PRICE.value,
        attempted_market="PH",
        attempted_source=_SOURCE,
        outcome=outcome,
        error_category=error_category,
        evaluated_offer_count=1 if success else 0,
        normalized_offer_count=1 if success else 0,
        returned_currencies=currencies if success else (),
        normalized_amount_minors=amounts if success else (),
        evidence_ids=evidence_ids if success else (),
        normalized_offer_digests=digests if success else (),
        observation_kind=observation_kind,
        trace=trace,
        raw_response_persisted=False,
    )
    return executions.cas_replace(completed, expected_revision=prepared.revision)


def _world(
    records: tuple[ResearchExecutionEvidence, ...],
    *,
    state: str = "completed",
    outcome: str = "succeeded",
    error_category: str | None = None,
    observation_kind: str | None = "production",
    execution_decision: str = DECISION_ID,
):
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    snapshot = _base_snapshot()
    snapshots.add(snapshot)
    conversations = InMemoryConversationRepository(clock=lambda: START)
    context = conversations.create(
        owner=_owner(),
        decision_context=snapshot.to_reference(),
    )
    executions = InMemoryAuthorizedExecutionRepository()
    evidence = InMemoryResearchExecutionEvidenceRepository()
    execution_id = authorized_execution_id(_AUTH_KEY)
    for record in records:
        evidence.save(record)
    stored = _install_execution(
        executions,
        execution_id=execution_id,
        state=state,
        outcome=outcome,
        error_category=error_category,
        evidence_ids=(
            tuple(record.evidence_id for record in records) if state == "completed" else ()
        ),
        observation_kind=observation_kind,
        decision_id=execution_decision,
    )
    service = CanonicalResearchResultsService(
        executions,
        evidence,
        snapshots,
        conversations,
        clock=lambda: START,
    )
    return {
        "service": service,
        "snapshots": snapshots,
        "conversations": conversations,
        "evidence": evidence,
        "executions": executions,
        "snapshot": snapshot,
        "context": context,
        "execution": stored,
        "execution_id": stored.execution_id,
    }


def _integrate(world, **overrides: object):
    values = {
        "execution_id": world["execution_id"],
        "owner": _owner(),
        "conversation_id": world["context"].conversation_id,
        "decision_id": DECISION_ID,
    }
    values.update(overrides)
    return world["service"].integrate(**values)


class _BoomSnapshots(InMemoryDecisionSnapshotRepository):
    def add(self, snapshot):  # noqa: ANN001
        if snapshot.context_version > 1:
            raise PersistenceError("snapshot persistence failed")
        return super().add(snapshot)


class _BoomConversations(InMemoryConversationRepository):
    def advance_verified_research_context(self, *args, **kwargs):  # noqa: ANN002
        raise ConversationContextDriftError("conversation", "binding failed")


class _BoomEvidence(InMemoryResearchExecutionEvidenceRepository):
    def require_production_evidence(self, evidence_id: str):  # noqa: ARG002
        raise PersistenceError("evidence persistence failed")


def test_fixture_evidence_is_deterministic_and_not_live() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    fact = NormalizedOfferFact(
        product_id=SONY_ID,
        variant_id="black",
        seller_identity="North Audio",
        amount_minor=18990,
        currency="USD",
        availability="in_stock",
        observed_at=START,
        normalized_offer_digest=_DIGEST,
        observation_kind="synthetic",
        source_mode=SourceMode.FIXTURE.value,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        capability=_PRICE.value,
        market="PH",
        source=_SOURCE,
    )
    first = evidence_from_adapter_fact(
        fact,
        execution_id=execution_id,
        decision_id=DECISION_ID,
        plan_id=_PLAN,
        created_at=START,
    )
    second = evidence_from_adapter_fact(
        fact,
        execution_id=execution_id,
        decision_id=DECISION_ID,
        plan_id=_PLAN,
        created_at=datetime(2030, 1, 2, tzinfo=UTC),
    )
    assert first.evidence_id == second.evidence_id
    assert first.evidence_id.startswith("research-exec-evidence:")
    assert first.normalized_offer_digest == _DIGEST
    assert first.normalized_offer_digest != first.evidence_id
    repository = InMemoryResearchExecutionEvidenceRepository()
    saved = repository.save(first)
    again = repository.save(second)
    assert again is saved
    assert repository.get(first.evidence_id) is saved
    names = {item.name for item in fields(ResearchExecutionEvidence)}
    assert "raw_response" not in names
    assert "claim_capability" not in names
    assert "probe_capability" not in names
    assert saved.raw_response_persisted is False
    assert saved.test_fixture is True
    assert saved.observation_kind == "synthetic"
    assert saved.source_mode is SourceMode.FIXTURE
    assert saved.product_id == SONY_ID
    assert saved.variant_id == "black"
    assert saved.seller_identity == "North Audio"
    assert saved.amount_minor == 18990
    assert saved.currency == "USD"
    assert saved.availability == "in_stock"
    assert saved.launch_evidence is False
    assert saved.activates_public_market is False
    with pytest.raises(FixtureEvidenceRejected):
        repository.require_production_evidence(saved.evidence_id)
    live_identity = {
        **saved._identity_payload(),  # noqa: SLF001
        "source_mode": SourceMode.LIVE.value,
    }
    with pytest.raises(ValueError, match="SourceMode.LIVE"):
        ResearchExecutionEvidence(
            evidence_id=research_execution_evidence_id(live_identity),
            execution_id=saved.execution_id,
            decision_id=saved.decision_id,
            plan_id=saved.plan_id,
            provider_id=saved.provider_id,
            capability=saved.capability,
            market=saved.market,
            source=saved.source,
            product_id=saved.product_id,
            variant_id=saved.variant_id,
            seller_identity=saved.seller_identity,
            amount_minor=saved.amount_minor,
            currency=saved.currency,
            availability=saved.availability,
            observed_at=saved.observed_at,
            normalized_offer_digest=saved.normalized_offer_digest,
            observation_kind="synthetic",
            test_fixture=True,
            source_mode=SourceMode.LIVE,
            raw_response_persisted=False,
            created_at=saved.created_at,
        )
    with pytest.raises(ValueError, match="launch evidence"):
        replace(saved, launch_evidence=True)
    with pytest.raises(ValueError, match="public market"):
        replace(saved, activates_public_market=True)
    with pytest.raises(ValueError, match="live evidence"):
        evidence_from_adapter_fact(
            replace(fact, observation_kind="live"),
            execution_id=execution_id,
            decision_id=DECISION_ID,
            plan_id=_PLAN,
            created_at=START,
        )
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert REAL_SHOPIFY_CALLS == 0


def test_production_evidence_resolves_and_updates_one_canonical_version() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    record = _evidence(execution_id=execution_id)
    world = _world((record,))
    before = world["snapshot"]
    result = _integrate(world)
    assert result.outcome == "canonical_results_updated"
    assert result.shopper_results_updated is True
    assert result.decision_id == DECISION_ID
    assert result.context_version == 2
    assert result.evidence_ids == (record.evidence_id,)
    updated = world["snapshots"].get_for_owner(DECISION_ID, 2, _owner())
    previous = world["snapshots"].get_for_owner(DECISION_ID, 1, _owner())
    assert previous is not None and updated is not None
    assert previous.context_version == 1
    assert updated.decision_id == previous.decision_id
    assert updated.context_version == previous.context_version + 1
    assert updated.owner.has_same_identity(previous.owner)
    assert updated.evaluated_product_ids == (SONY_ID, BOSE_ID, SENN_ID)
    assert updated.canonical_piqscore_set_sha256 == before.canonical_piqscore_set_sha256
    assert updated.recommendation.snapshot_sha256 == before.recommendation.snapshot_sha256
    assert updated.recommendation.best_piq_product_id == SONY_ID
    assert updated.recommendation.alternative_product_ids == (BOSE_ID, SENN_ID)
    assert updated.recommendation.decision == before.recommendation.decision
    assert record.evidence_id in updated.evidence_ids
    resolved = world["evidence"].get(record.evidence_id)
    assert resolved == record
    assert resolved in tuple(
        world["evidence"].get(item) for item in updated.evidence_ids if item == record.evidence_id
    )
    added = next(item for item in updated.evidence if item.evidence_id == record.evidence_id)
    assert added.captured_at == START
    assert added.freshness == "fresh"
    assert "Observed listing price 18990 USD." in added.fact
    assert "Seller identity: North Audio." in added.fact
    assert "Observed availability: in_stock." in added.fact
    for banned in ("cheapest", "best deal", "final price", "delivered price", "free shipping"):
        assert banned not in added.fact.lower()
    economics = next(item for item in updated.offer_economics if item.product_id == SONY_ID)
    assert economics.listing.amount_minor == 18990
    assert economics.listing.currency == "USD"
    assert economics.listing.status == "verified"
    assert economics.listing.label == "observed listing price"
    assert economics.price_state == "price_before_shipping"
    assert economics.dominant_amount_minor == 18990
    assert economics.freshness == "fresh"
    for line in (economics.shipping, economics.taxes, economics.voucher, economics.import_charges):
        assert line is not None
        assert line.status == "unknown"
        assert line.amount_minor is None
        assert line.applied is False
    assert "shipping" in economics.unknowns
    assert "tax" in economics.unknowns
    assert "import" in economics.unknowns
    assert "voucher" in economics.unknowns
    assert "promotions" in economics.unknowns
    assert "checkout cost" in economics.unknowns
    context = world["conversations"].get(world["context"].conversation_id)
    assert context is not None
    assert context.decision_context == updated.to_reference()
    assert context.owner is not None
    assert context.owner.has_same_identity(_owner())
    assert world["evidence"].require_production_evidence(record.evidence_id) == record


def test_retry_and_concurrent_integration_create_one_version() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    record = _evidence(execution_id=execution_id)
    world = _world((record,))
    first = _integrate(world)
    second = _integrate(world)
    assert first.outcome == "canonical_results_updated"
    assert second.outcome == "already_integrated"
    assert second.context_version == 2
    assert world["snapshots"].get(DECISION_ID, 3) is None
    again = _world((_evidence(execution_id=authorized_execution_id(_AUTH_KEY)),))
    results: list[object] = []

    def _run() -> None:
        results.append(_integrate(again))

    threads = [Thread(target=_run), Thread(target=_run)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    outcomes = {item.outcome for item in results}  # type: ignore[attr-defined]
    assert outcomes <= {"canonical_results_updated", "already_integrated"}
    assert "canonical_results_updated" in outcomes
    assert again["snapshots"].get(DECISION_ID, 3) is None
    assert again["snapshots"].get(DECISION_ID, 2) is not None


def test_fixture_and_non_success_executions_preserve_the_prior_decision() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    fixture = _evidence(
        execution_id=execution_id,
        test_fixture=True,
        observation_kind="synthetic",
    )
    synthetic = _world((fixture,), observation_kind="synthetic")
    refused = _integrate(synthetic)
    assert refused.outcome == "fixture_evidence_rejected"
    assert refused.shopper_results_updated is False
    assert synthetic["snapshots"].get(DECISION_ID, 2) is None

    labeled = _world((fixture,), observation_kind="production")
    labeled_result = _integrate(labeled)
    assert labeled_result.outcome == "fixture_evidence_rejected"
    assert labeled["snapshots"].get(DECISION_ID, 2) is None

    outside = _evidence(execution_id=execution_id, product_id="airpods-max")
    outside_world = _world((outside,))
    outside_result = _integrate(outside_world)
    assert outside_result.outcome == "canonical_reevaluation_required"
    assert outside_world["evidence"].get(outside.evidence_id) == outside
    assert outside_world["snapshots"].get(DECISION_ID, 2) is None
    assert _integrate(outside_world).outcome == "canonical_reevaluation_required"

    ambiguous = _evidence(execution_id=execution_id, variant_id="silver")
    ambiguous_world = _world((ambiguous,))
    assert _integrate(ambiguous_world).outcome == "ambiguous_variant"
    assert ambiguous_world["snapshots"].get(DECISION_ID, 2) is None

    discovery = _evidence(
        execution_id=execution_id,
        product_id="new-product",
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        variant_id=None,
    )
    discovery_world = _world((discovery,))
    assert _integrate(discovery_world).outcome == "canonical_reevaluation_required"


def test_failed_timeout_and_unknown_outcomes_do_not_replace_results() -> None:
    cases = (
        ("failed", "failed", "normalization_refused"),
        ("failed", "timed_out", "timeout"),
        ("outcome_unknown", "outcome_unknown", "outcome_unknown"),
    )
    for state, outcome, category in cases:
        world = _world((), state=state, outcome=outcome, error_category=category)
        result = _integrate(world)
        assert result.outcome == "prior_decision_preserved"
        assert result.shopper_results_updated is False
        assert world["snapshots"].get(DECISION_ID, 2) is None
        context = world["conversations"].get(world["context"].conversation_id)
        assert context is not None
        assert context.decision_context is not None
        assert context.decision_context.context_version == 1


def test_persistence_and_owner_failures_keep_history() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    record = _evidence(execution_id=execution_id)
    evidence_world = _world((record,))
    evidence_world["service"]._evidence = _BoomEvidence()  # noqa: SLF001
    unresolved = _integrate(evidence_world)
    assert unresolved.outcome == "evidence_unresolved"
    assert evidence_world["snapshots"].get(DECISION_ID, 2) is None

    snapshot_world = _world((record,))
    boom_snapshots = _BoomSnapshots(clock=lambda: START)
    boom_snapshots.add(snapshot_world["snapshot"])
    snapshot_world["service"]._snapshots = boom_snapshots  # noqa: SLF001
    failed_snapshot = _integrate(snapshot_world)
    assert failed_snapshot.outcome == "snapshot_persistence_failed"
    assert boom_snapshots.get(DECISION_ID, 2) is None
    context = snapshot_world["conversations"].get(snapshot_world["context"].conversation_id)
    assert context is not None
    assert context.decision_context is not None
    assert context.decision_context.context_version == 1

    binding_world = _world((record,))
    boom_conversations = _BoomConversations(clock=lambda: START)
    moved = boom_conversations.create(
        owner=_owner(),
        decision_context=binding_world["snapshot"].to_reference(),
    )
    binding_world["service"]._conversations = boom_conversations  # noqa: SLF001
    binding_world["context"] = moved
    failed_bind = _integrate(binding_world)
    assert failed_bind.outcome == "conversation_binding_failed"
    assert binding_world["snapshots"].get(DECISION_ID, 1) is not None
    assert binding_world["snapshots"].get(DECISION_ID, 2) is not None
    rebound = boom_conversations.get(moved.conversation_id)
    assert rebound is not None
    assert rebound.decision_context is not None
    assert rebound.decision_context.context_version == 1

    owner_world = _world((record,))
    wrong = _integrate(owner_world, owner=_owner("other-guest"))
    assert wrong.outcome == "wrong_owner"
    assert owner_world["snapshots"].get(DECISION_ID, 2) is None

    decision_world = _world((record,))
    different = _integrate(
        decision_world,
        decision_id="00000000-0000-4000-8000-000000000295",
    )
    assert different.outcome == "different_decision"
    assert decision_world["snapshots"].get(DECISION_ID, 2) is None


def test_trace_evidence_references_resolve_and_digests_stay_digests() -> None:
    execution_id = authorized_execution_id(_AUTH_KEY)
    record = _evidence(execution_id=execution_id, test_fixture=True, observation_kind="synthetic")
    executions = InMemoryAuthorizedExecutionRepository()
    evidence = InMemoryResearchExecutionEvidenceRepository()
    evidence.save(record)
    stored = _install_execution(
        executions,
        execution_id=execution_id,
        state="completed",
        outcome="succeeded",
        error_category=None,
        evidence_ids=(),
        observation_kind="synthetic",
        digests=(_DIGEST,),
    )
    missing = attach_execution_evidence_references(
        executions,
        evidence,
        stored.execution_id,
        ("research-exec-evidence:" + ("ef" * 32),),
    )
    assert missing.attached is False
    assert missing.reason == "evidence_unresolved"
    untouched = executions.get(stored.execution_id)
    assert untouched is not None
    assert untouched.evidence_ids == ()
    assert untouched.outcome == "succeeded"
    attached = attach_execution_evidence_references(
        executions,
        evidence,
        stored.execution_id,
        (record.evidence_id,),
    )
    assert attached.attached is True
    current = executions.get(stored.execution_id)
    assert current is not None
    assert current.evidence_ids == (record.evidence_id,)
    assert current.normalized_offer_digests == (_DIGEST,)
    assert _DIGEST not in current.evidence_ids
    assert current.trace is not None
    assert current.trace.steps[0].evidence_ids == (record.evidence_id,)
    assert evidence.get(current.evidence_ids[0]) == record
    assert current.outcome == "succeeded"

    class _LostRace(InMemoryAuthorizedExecutionRepository):
        def cas_replace(self, record, *, expected_revision: int):  # noqa: ANN001
            raise AuthorizedExecutionRevisionConflict(record.execution_id, expected_revision)

    raced = _LostRace()
    raced._rows = executions._rows  # noqa: SLF001
    race = attach_execution_evidence_references(
        raced,
        evidence,
        stored.execution_id,
        (record.evidence_id,),
    )
    assert race.reason == "already_attached"
    assert executions.get(stored.execution_id).outcome == "succeeded"  # type: ignore[union-attr]
