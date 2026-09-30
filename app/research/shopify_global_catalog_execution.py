"""Shopify Global Catalog execution adapter — Sprint 38.

This module is the certified PH catalog path from a live-start claim to a
durable outcome. It is not a generic ``StaticResearchProvider.execute``.

Production composition cannot reach the transport. The only caller that may
invoke a transport is an explicit :class:`BoundedFakeTransportPermit`. That
permit does not flip production flags, does not label the result live, and
does not make live execution operational.

Crash boundaries:

- Before the attempt-start commit, the execution is still
  ``claimed_for_attempt``. When that claim expires, the same execution can
  be reclaimed. No external HTTP has been recorded.
- The attempt-start commit moves the row to ``running`` immediately before
  transport. A crash after that commit and before the outcome commit cannot
  prove whether HTTP happened. Recovery does not replay HTTP. It fails
  closed to ``outcome_unknown`` after the claim lease expires, does not
  record breaker success or failure, and does not clear a HALF_OPEN probe
  lease early.
- HTTP runs outside the database transaction. The outcome transaction
  reloads the execution, checks the active claim capability, checks the
  HALF_OPEN probe when needed, writes the trace, updates the breaker, and
  releases the claim. A lost compare-and-swap does not overwrite a terminal
  row and does not invent success.

Real Shopify calls in this module's production entry point stay zero.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Literal

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.marketplace_data import SourceMode
from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_execution import (
    ResearchExecutionPlan,
    ResearchExecutionTrace,
    ResearchExecutionTraceStep,
    ResearchProviderStep,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.infrastructure.persistence.errors import PersistenceError
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.marketplace.normalization.shopify_global_catalog import (
    ShopifyNormalizationRefusal,
    ShopifyNormalizedOffer,
    normalize_shopify_global_catalog_offer,
)
from app.research.authorized_execution_repository import (
    AuthorizedExecutionRevisionConflict,
    DurableAuthorizedExecution,
    InMemoryAuthorizedExecutionRepository,
)
from app.research.digest import stable_sha256
from app.research.live_start_claim import (
    LIVE_CONNECTOR_CLEANUP_MARGIN,
    SHOPIFY_LIVE_HTTP_TIMEOUT,
    ActiveClaimCheck,
    ClaimTransaction,
    InMemoryClaimTransaction,
    OperationalClaimTransaction,
    execution_claim_digest,
    validate_active_execution_claim,
    validate_active_half_open_probe,
)
from app.research.reliability_repository import (
    InMemoryResearchReliabilityRepository,
    ReliabilityRevisionConflict,
)
from app.research.reliability_state import (
    BreakerPolicy,
    ProviderReliabilityState,
    assess_execution_permission,
    record_failure,
    record_success,
)
from app.research.shopify_global_catalog_ph_probe import (
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    PH_COUNTRY,
    SEARCH_TOOL,
    ProbeContractError,
    anonymous_http_headers,
    build_get_product_arguments,
    build_jsonrpc_request,
    build_search_catalog_arguments,
    products_from_catalog_payload,
    variants_from_product,
)
from app.research.shopify_global_catalog_provider import (
    SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
)
from app.research.shopify_global_catalog_reliability import classify_shopify_catalog_envelope
from app.research.shopify_global_catalog_transport import (
    CatalogTransportResult,
    JsonPostTransport,
)
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    production_live_mode_assessment,
)
from app.services.research_authorization import owner_binding_digest
from app.services.research_execution import authorized_execution_id
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

SHOPIFY_EXECUTION_ADAPTER_IMPLEMENTED = True
SHOPIFY_HTTP_TIMEOUT_SECONDS = SHOPIFY_LIVE_HTTP_TIMEOUT.total_seconds()
RAW_SHOPIFY_RESPONSE_PERSISTED = False
REAL_SHOPIFY_CALLS = 0
FAKE_TRANSPORT_OBSERVATION_KIND = "synthetic"
_SUPPORTED = frozenset(SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES)
_ALLOWED_TOOLS = frozenset({SEARCH_TOOL, GET_PRODUCT_TOOL})
_UNKNOWN_COSTS = ("shipping", "tax", "import", "voucher")
_TERMINAL = frozenset({"completed", "failed", "outcome_unknown"})


@dataclass(frozen=True, slots=True)
class BoundedFakeTransportPermit:
    """Test permit for an injected transport. Not a production live switch."""

    marker: Literal["bounded_fake_transport"] = "bounded_fake_transport"

    def __post_init__(self) -> None:
        if self.marker != "bounded_fake_transport":
            raise ValueError("bounded fake transport permit is not a production live switch")


@dataclass(frozen=True, slots=True)
class ShopifyCatalogAttempt:
    """Server-trusted attempt. Market, provider, source, and currency are not overrides.

    ``harness_operational_status`` is the breaker permission input for this
    bounded permit. It does not change the production provider descriptor.
    """

    permit: BoundedFakeTransportPermit
    authorization: ResearchAuthorization
    owner: ConversationOwner
    plan: ResearchExecutionPlan
    step: ResearchProviderStep
    source: str
    operation: str
    claim_capability: str
    now: datetime
    harness_operational_status: ConnectorOperationalStatus
    catalog_query: str | None = None
    product_id: str | None = None
    probe_capability: str | None = None
    finished_at: datetime | None = None
    kill_switch: KillSwitch = KillSwitch()


@dataclass(frozen=True, slots=True)
class ShopifyExecutionResult:
    """Adapter result. A fake transport success is not live evidence."""

    attempted: bool
    transport_invoked: bool
    persisted: bool
    state: str | None
    block_reason: str | None
    outcome: str | None = None
    error_category: str | None = None
    failure_kind: str | None = None
    evaluated_offer_count: int = 0
    normalized_offer_count: int = 0
    returned_currencies: tuple[str, ...] = ()
    observation_kind: str | None = None
    source_mode_live: bool = False
    raw_response_persisted: bool = False
    live_research_execution_operational: bool = False
    prior_decision_preserved: bool = True
    retry_count: int = 0
    real_shopify_call_count: int = 0
    claim_released: bool = False
    trace: ResearchExecutionTrace | None = None
    blocking_reasons: tuple[str, ...] = ()
    unknown_cost_components: tuple[str, ...] = ()
    transport_outcome_ambiguous: bool = False

    def __post_init__(self) -> None:
        if self.real_shopify_call_count != 0 or REAL_SHOPIFY_CALLS != 0:
            raise ValueError("this slice cannot record a real Shopify call")
        if self.retry_count != 0:
            raise ValueError("the Shopify path does not retry")
        if self.raw_response_persisted or RAW_SHOPIFY_RESPONSE_PERSISTED:
            raise ValueError("raw Shopify responses must not be persisted")
        if self.source_mode_live or self.live_research_execution_operational:
            raise ValueError("this result is not live execution")
        if self.observation_kind == "live":
            raise ValueError("a fake transport result cannot be labeled live")
        if LIVE_RESEARCH_EXECUTION_OPERATIONAL:
            raise ValueError("live research execution is not operational")
        if self.transport_invoked and not self.attempted:
            raise ValueError("transport implies an attempt")
        if self.persisted and self.state not in _TERMINAL:
            raise ValueError("a persisted outcome is terminal")
        if not self.prior_decision_preserved:
            raise ValueError("execution must preserve the prior decision")
        if self.evaluated_offer_count < 0 or self.normalized_offer_count < 0:
            raise ValueError("offer counts cannot be negative")

    @property
    def durable_success(self) -> bool:
        return self.persisted and self.state == "completed" and self.outcome == "succeeded"


@dataclass(frozen=True, slots=True)
class _PreparedCall:
    execution: DurableAuthorizedExecution
    payload: dict[str, Any]
    headers: dict[str, str]
    request_digest: str


@dataclass(frozen=True, slots=True)
class _Interpreted:
    success: bool
    attempt_status: Literal["succeeded", "failed", "timed_out"]
    failure_kind: ConnectorFailureKind | None
    error_category: str | None
    offers: tuple[ShopifyNormalizedOffer, ...] = ()


class ShopifyCatalogExecutionService:
    """Claim holder to durable Shopify outcome. Transport is injected."""

    def __init__(
        self,
        transaction_factory: Callable[[], ClaimTransaction],
        transport: JsonPostTransport,
        *,
        policy: BreakerPolicy | None = None,
    ) -> None:
        self._transactions = transaction_factory
        self._transport = transport
        self._policy = policy or BreakerPolicy()

    def execute(self, attempt: ShopifyCatalogAttempt) -> ShopifyExecutionResult:
        """Validate, then transport once, then commit the outcome."""

        local = _local_refusal(attempt)
        if local is not None:
            return local
        transaction = self._transactions()
        try:
            try:
                transaction.lock_for_claim()
                prepared = self._begin_attempt(transaction, attempt)
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused("attempt_persistence_unavailable")
            if isinstance(prepared, ShopifyExecutionResult):
                transaction.rollback()
                return prepared
            try:
                transaction.commit()
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused("attempt_persistence_unavailable")
        finally:
            transaction.close()

        try:
            response = self._transport.post_json(
                GLOBAL_CATALOG_ENDPOINT,
                prepared.headers,
                prepared.payload,
                SHOPIFY_HTTP_TIMEOUT_SECONDS,
            )
        except Exception:
            return _refused(
                "ambiguous_transport_outcome",
                attempted=True,
                state="running",
                transport_outcome_ambiguous=True,
            )
        interpreted = _interpret(response, checked_at=attempt.finished_at or attempt.now)
        return self._commit_outcome(attempt, prepared, interpreted, transport_invoked=True)

    def reconcile_ambiguous(self, attempt: ShopifyCatalogAttempt) -> ShopifyExecutionResult:
        """Fail closed after a lost post-HTTP outcome. Does not call transport."""

        if attempt.now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        transaction = self._transactions()
        try:
            try:
                transaction.lock_for_claim()
                execution = transaction.load_execution(_execution_id(attempt))
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused("outcome_persistence_unavailable")
            if execution is None:
                transaction.rollback()
                return _refused("execution_not_prepared")
            if execution.state != "running":
                transaction.rollback()
                if execution.state in _TERMINAL:
                    reason = "execution_terminal"
                else:
                    reason = "execution_not_running"
                return _refused(reason, state=execution.state)
            if execution.claim_expires_at is not None and attempt.now < execution.claim_expires_at:
                transaction.rollback()
                return _refused(
                    "attempt_still_claimed",
                    attempted=True,
                    state="running",
                )
            finished = attempt.finished_at or attempt.now
            stored = _terminal_record(
                execution,
                attempt=attempt,
                finished_at=finished,
                outcome="outcome_unknown",
                error_category="outcome_unknown",
                attempt_status="outcome_unknown",
                offers=(),
                request_digest=execution.request_digest,
                observation_kind=None,
            )
            try:
                saved = transaction.cas_execution(stored, expected_revision=execution.revision)
                transaction.commit()
            except AuthorizedExecutionRevisionConflict:
                transaction.rollback()
                return _refused("stale_outcome_rejected", attempted=True, state="running")
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused(
                    "outcome_persistence_unavailable",
                    attempted=True,
                    state="running",
                )
        finally:
            transaction.close()
        return _from_stored(saved, transport_invoked=False)

    def _begin_attempt(
        self,
        transaction: ClaimTransaction,
        attempt: ShopifyCatalogAttempt,
    ) -> _PreparedCall | ShopifyExecutionResult:
        execution = transaction.load_execution(_execution_id(attempt))
        refusal = _pre_transport_reason(transaction, attempt, execution)
        if refusal is not None:
            return _refused(
                refusal,
                state=None if execution is None else execution.state,
            )
        assert execution is not None
        try:
            payload = _catalog_payload(attempt)
        except ProbeContractError:
            return _refused("catalog_contract_rejected", state=execution.state)
        headers = anonymous_http_headers()
        if "Authorization" in headers or any(
            key.lower() in {"authorization", "signature", "x-signature"} for key in headers
        ):
            return _refused("catalog_contract_rejected", state=execution.state)
        digest = _request_digest(attempt)
        running = replace(
            execution,
            state="running",
            updated_at=attempt.now,
            attempt_started_at=attempt.now,
            attempted_provider_id=attempt.step.provider_id,
            attempted_capability=attempt.step.capability.value,
            attempted_market=attempt.step.market,
            attempted_source=attempt.source,
            request_digest=digest,
        )
        try:
            stored = transaction.cas_execution(running, expected_revision=execution.revision)
        except AuthorizedExecutionRevisionConflict:
            return _refused("stale_claim_rejected", state=execution.state)
        return _PreparedCall(
            execution=stored,
            payload=payload,
            headers=headers,
            request_digest=digest,
        )

    def _commit_outcome(
        self,
        attempt: ShopifyCatalogAttempt,
        prepared: _PreparedCall,
        interpreted: _Interpreted,
        *,
        transport_invoked: bool,
    ) -> ShopifyExecutionResult:
        finished = attempt.finished_at or attempt.now
        transaction = self._transactions()
        try:
            try:
                transaction.lock_for_claim()
                execution = transaction.reload_execution(prepared.execution.execution_id)
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused(
                    "outcome_persistence_unavailable",
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
            if execution is None or execution.state != "running":
                transaction.rollback()
                return _refused(
                    "execution_terminal" if execution is not None else "execution_not_prepared",
                    attempted=True,
                    state=None if execution is None else execution.state,
                    transport_invoked=transport_invoked,
                )
            holder = _validate_running_claim(execution, attempt.claim_capability, finished)
            if not holder.valid:
                transaction.rollback()
                return _refused(
                    holder.reason or "execution_claim_expired",
                    attempted=True,
                    state=execution.state,
                    transport_invoked=transport_invoked,
                )
            breaker = transaction.load_breaker(
                attempt.step.provider_id,
                attempt.step.market or PH_COUNTRY,
                now=finished,
            )
            probe_reason = _probe_reason(breaker, attempt, finished)
            if probe_reason is not None:
                transaction.rollback()
                return _refused(
                    probe_reason,
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
            if interpreted.success and breaker.state is CircuitBreakerState.OPEN:
                transaction.rollback()
                return _refused(
                    "circuit_open",
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
            next_breaker = _next_breaker(
                breaker,
                interpreted,
                now=finished,
                policy=self._policy,
            )
            record = _terminal_record(
                execution,
                attempt=attempt,
                finished_at=finished,
                outcome=interpreted.attempt_status,
                error_category=interpreted.error_category,
                attempt_status=interpreted.attempt_status,
                offers=interpreted.offers,
                request_digest=prepared.request_digest,
                observation_kind=FAKE_TRANSPORT_OBSERVATION_KIND,
            )
            try:
                saved = transaction.cas_execution(record, expected_revision=execution.revision)
                transaction.cas_breaker(next_breaker, expected_revision=breaker.revision)
                transaction.commit()
            except AuthorizedExecutionRevisionConflict:
                transaction.rollback()
                return _refused(
                    "stale_outcome_rejected",
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
            except ReliabilityRevisionConflict:
                transaction.rollback()
                return _refused(
                    "stale_outcome_rejected",
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
            except (PersistenceError, OperationalError, DBAPIError):
                transaction.rollback()
                return _refused(
                    "outcome_persistence_unavailable",
                    attempted=True,
                    state="running",
                    transport_invoked=transport_invoked,
                )
        finally:
            transaction.close()
        return _from_stored(
            saved,
            transport_invoked=transport_invoked,
            failure_kind=interpreted.failure_kind,
            unknown_costs=_unknown_costs(interpreted.offers) if interpreted.success else (),
        )


def execute_production_shopify_catalog(
    transport: JsonPostTransport,
) -> ShopifyExecutionResult:
    """Production entry. It never calls ``transport``.

    Gates stay closed in this repository. Even an empty reason list does not
    call the transport: production composition is not wired to the adapter.
    """

    del transport
    reasons = production_shopify_execution_block_reasons()
    if not reasons:
        reasons = ("production_execution_not_wired",)
    return _refused(reasons[0], blocking_reasons=reasons)


def production_shopify_execution_block_reasons() -> tuple[str, ...]:
    """Current production gates. This reads constants and does not connect."""

    reasons: list[str] = list(production_live_mode_assessment().reasons)
    if SHOPPING_RESEARCH_EXECUTION_MODE != "live" and "mode_not_live" not in reasons:
        reasons.append("mode_not_live")
    if not SHOPIFY_LIVE_CALL_PERMITTED:
        reasons.append("shopify_live_call_not_permitted")
    if not PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED:
        reasons.append("production_ucp_profile_undeployed")
    if LIVE_RESEARCH_EXECUTION_OPERATIONAL:
        reasons.append("live_flag_unexpectedly_enabled")
    return tuple(dict.fromkeys(reasons))


def in_memory_shopify_execution(
    executions: InMemoryAuthorizedExecutionRepository,
    reliability: InMemoryResearchReliabilityRepository,
    conversations: InMemoryConversationRepository,
    transport: JsonPostTransport,
    *,
    policy: BreakerPolicy | None = None,
) -> ShopifyCatalogExecutionService:
    """Test service. A new transaction sees the shared in-memory rows."""

    def factory() -> InMemoryClaimTransaction:
        return InMemoryClaimTransaction(executions, reliability, conversations)

    return ShopifyCatalogExecutionService(factory, transport, policy=policy)


def operational_shopify_execution(
    session_factory: sessionmaker,
    transport: JsonPostTransport,
    *,
    policy: BreakerPolicy | None = None,
) -> ShopifyCatalogExecutionService:
    """Repository-backed service. Not production composition."""

    def factory() -> OperationalClaimTransaction:
        return OperationalClaimTransaction(session_factory)

    return ShopifyCatalogExecutionService(factory, transport, policy=policy)


def _execution_id(attempt: ShopifyCatalogAttempt) -> str:
    return authorized_execution_id(attempt.authorization.idempotency_key)


def _local_refusal(attempt: ShopifyCatalogAttempt) -> ShopifyExecutionResult | None:
    if attempt.permit.marker != "bounded_fake_transport":
        return _refused("bounded_fake_transport_required")
    if attempt.now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    finished = attempt.finished_at
    if finished is not None and (finished.tzinfo is None or finished < attempt.now):
        return _refused("finished_at_invalid")
    if attempt.step.capability not in _SUPPORTED:
        return _refused("capability_not_supported")
    if attempt.operation == FORBIDDEN_LOOKUP_TOOL or attempt.operation not in _ALLOWED_TOOLS:
        return _refused("catalog_tool_forbidden")
    if attempt.step.provider_id != SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID:
        return _refused("provider_not_shopify")
    if attempt.step.market != PH_COUNTRY:
        return _refused("market_not_supported")
    source_matches = attempt.source in attempt.step.source_identities
    if attempt.source != "shopify_global_catalog" or not source_matches:
        return _refused("source_not_supported")
    if attempt.operation == SEARCH_TOOL:
        if not (attempt.catalog_query or "").strip() or attempt.product_id:
            return _refused("catalog_query_required")
    elif not attempt.product_id or "," in attempt.product_id or not attempt.product_id.strip():
        return _refused("catalog_product_id_invalid")
    return None


def _pre_transport_reason(
    transaction: ClaimTransaction,
    attempt: ShopifyCatalogAttempt,
    execution: DurableAuthorizedExecution | None,
) -> str | None:
    if execution is None:
        return "execution_not_prepared"
    if execution.plan_id != attempt.plan.plan_id:
        return "authorization_plan_conflict"
    if (
        execution.authorization_id != attempt.authorization.authorization_id
        or execution.authorization_version != attempt.authorization.authorization_version
        or execution.decision_id != attempt.plan.decision_id
        or execution.decision_id != attempt.authorization.decision_id
    ):
        return "execution_pin_mismatch"
    if not any(_same_step(attempt.step, step) for step in attempt.plan.eligible_steps):
        return "plan_target_mismatch"
    if execution.state == "running":
        return "ambiguous_outcome_requires_reconciliation"
    if execution.state in _TERMINAL:
        return "execution_terminal"
    claim = validate_active_execution_claim(
        execution,
        claim_capability=attempt.claim_capability,
        now=attempt.now,
    )
    if not claim.valid:
        return claim.reason or "execution_not_claimed"
    if not _budget_ok(execution.claim_expires_at, attempt.now):
        return "claim_budget_insufficient"
    authorization_reason = _authorization_reason(transaction, attempt, execution)
    if authorization_reason is not None:
        return authorization_reason
    breaker = transaction.load_breaker(
        attempt.step.provider_id,
        attempt.step.market or PH_COUNTRY,
        now=attempt.now,
    )
    permission = assess_execution_permission(
        breaker,
        operational_status=attempt.harness_operational_status,
        kill_switch=attempt.kill_switch,
        now=attempt.now,
    )
    if not permission.execution_permitted:
        return permission.block_reason
    return _probe_reason(permission.breaker, attempt, attempt.now)


def _probe_reason(
    breaker: ProviderReliabilityState,
    attempt: ShopifyCatalogAttempt,
    now: datetime,
) -> str | None:
    if breaker.state is CircuitBreakerState.HALF_OPEN:
        if not attempt.probe_capability:
            return "half_open_probe_not_active"
        check = validate_active_half_open_probe(
            breaker,
            claim_capability=attempt.probe_capability,
            now=now,
        )
        if not check.valid:
            return check.reason
        if not _budget_ok(breaker.half_open_probe_expires_at, now):
            return "claim_budget_insufficient"
        return None
    if attempt.probe_capability is not None:
        return "half_open_probe_not_active"
    return None


def _budget_ok(expires_at: datetime | None, now: datetime) -> bool:
    if expires_at is None:
        return False
    return expires_at - now >= SHOPIFY_LIVE_HTTP_TIMEOUT + LIVE_CONNECTOR_CLEANUP_MARGIN


def _authorization_reason(
    transaction: ClaimTransaction,
    attempt: ShopifyCatalogAttempt,
    execution: DurableAuthorizedExecution,
) -> str | None:
    conversation = transaction.load_conversation(attempt.authorization.conversation_id)
    if conversation is None:
        return "authorization_conversation_missing"
    if conversation.owner is None or not conversation.owner.has_same_identity(attempt.owner):
        return "wrong_owner"
    matches = [
        item
        for item in conversation.research_authorizations
        if item.authorization_id == attempt.authorization.authorization_id
    ]
    if len(matches) != 1:
        return "authorization_not_found"
    stored = matches[0]
    if stored.status != "consumed":
        return "authorization_not_consumed"
    if (
        stored.authorization_version != execution.authorization_version
        or stored.decision_id != execution.decision_id
        or stored.idempotency_key != attempt.authorization.idempotency_key
        or stored.scope_digest != attempt.plan.scope_digest
    ):
        return "authorization_identity_mismatch"
    if owner_binding_digest(attempt.owner) != stored.owner_binding:
        return "wrong_owner"
    if execution.execution_id != authorized_execution_id(stored.idempotency_key):
        return "consumed_authorization_execution_mismatch"
    return None


def _validate_running_claim(
    record: DurableAuthorizedExecution,
    claim_capability: str,
    now: datetime,
) -> ActiveClaimCheck:
    if record.state != "running":
        return ActiveClaimCheck(False, "execution_not_running")
    if record.claim_expires_at is None or now >= record.claim_expires_at:
        return ActiveClaimCheck(False, "execution_claim_expired")
    try:
        expected = execution_claim_digest(claim_capability)
    except ValueError:
        return ActiveClaimCheck(False, "execution_claim_identity_mismatch")
    if record.claim_digest != expected:
        return ActiveClaimCheck(False, "execution_claim_identity_mismatch")
    return ActiveClaimCheck(True, None)


def _catalog_payload(attempt: ShopifyCatalogAttempt) -> dict[str, Any]:
    if attempt.operation == SEARCH_TOOL:
        arguments = build_search_catalog_arguments((attempt.catalog_query or "").strip())
    else:
        arguments = build_get_product_arguments((attempt.product_id or "").strip())
    return build_jsonrpc_request(attempt.operation, arguments, request_id=1)


def _request_digest(attempt: ShopifyCatalogAttempt) -> str:
    query = (attempt.catalog_query or "").strip() or None
    product_id = (attempt.product_id or "").strip() or None
    return stable_sha256(
        {
            "kind": "shopify_catalog_request_v1",
            "endpoint": GLOBAL_CATALOG_ENDPOINT,
            "tool": attempt.operation,
            "timeout_seconds": SHOPIFY_HTTP_TIMEOUT_SECONDS,
            "query_digest": None if query is None else stable_sha256({"query": query}),
            "product_id_digest": (
                None if product_id is None else stable_sha256({"product_id": product_id})
            ),
        }
    )


def _interpret(response: CatalogTransportResult, *, checked_at: datetime) -> _Interpreted:
    if response.timed_out:
        return _Interpreted(False, "timed_out", ConnectorFailureKind.TIMEOUT, "timeout")
    if response.malformed or response.payload is None:
        return _Interpreted(False, "failed", ConnectorFailureKind.UNKNOWN, "malformed_jsonrpc")
    status = response.status_code
    if status == 429:
        return _Interpreted(False, "failed", ConnectorFailureKind.RATE_LIMIT, "rate_limit")
    if status in {401, 403}:
        return _Interpreted(False, "failed", ConnectorFailureKind.CREDENTIAL, "credential")
    if 500 <= status <= 599:
        return _Interpreted(False, "failed", ConnectorFailureKind.UNAVAILABLE, "unavailable")
    if status != 200:
        return _Interpreted(False, "failed", ConnectorFailureKind.UNKNOWN, "unknown")
    envelope = classify_shopify_catalog_envelope(response.payload)
    if envelope.fail_closed:
        kind = envelope.failure_kind or ConnectorFailureKind.UNKNOWN
        status_name: Literal["failed", "timed_out"] = "failed"
        category = envelope.reason or kind.value
        if kind is ConnectorFailureKind.UNKNOWN and envelope.reason == "malformed_jsonrpc":
            category = "malformed_jsonrpc"
        return _Interpreted(False, status_name, kind, category)
    offers, refusal = _normalize_all(response.payload, checked_at=checked_at)
    if refusal is not None or not offers:
        return _Interpreted(
            False,
            "failed",
            ConnectorFailureKind.PARTIAL,
            refusal or "normalization_refusal",
        )
    return _Interpreted(True, "succeeded", None, None, tuple(offers))


def _normalize_all(
    payload: Mapping[str, Any],
    *,
    checked_at: datetime,
) -> tuple[tuple[ShopifyNormalizedOffer, ...], str | None]:
    products = products_from_catalog_payload(dict(payload))
    if not products:
        return (), "normalization_refusal"
    offers: list[ShopifyNormalizedOffer] = []
    for product in products:
        variants = variants_from_product(product)
        if not variants:
            return (), "normalization_refusal"
        for variant in variants:
            try:
                offer = normalize_shopify_global_catalog_offer(
                    product,
                    variant,
                    checked_at=checked_at,
                    observation_kind=FAKE_TRANSPORT_OBSERVATION_KIND,
                    ph_query_context=True,
                )
            except ShopifyNormalizationRefusal as exc:
                return (), exc.reason
            if (
                offer.source.observation_kind == "live"
                or offer.source.source_mode is SourceMode.LIVE
            ):
                return (), "live_observation_forbidden"
            offers.append(offer)
    return tuple(offers), None


def _next_breaker(
    state: ProviderReliabilityState,
    interpreted: _Interpreted,
    *,
    now: datetime,
    policy: BreakerPolicy,
) -> ProviderReliabilityState:
    if interpreted.success:
        return record_success(state, now=now)
    assert interpreted.failure_kind is not None
    updated = record_failure(state, interpreted.failure_kind, now=now, policy=policy)
    if updated.state is CircuitBreakerState.HALF_OPEN and updated.half_open_probe_claim_digest:
        return replace(
            updated,
            half_open_probe_claim_digest=None,
            half_open_probe_claimed_at=None,
            half_open_probe_expires_at=None,
        )
    return updated


def _terminal_record(
    execution: DurableAuthorizedExecution,
    *,
    attempt: ShopifyCatalogAttempt,
    finished_at: datetime,
    outcome: str,
    error_category: str | None,
    attempt_status: str,
    offers: tuple[ShopifyNormalizedOffer, ...],
    request_digest: str | None,
    observation_kind: str | None,
) -> DurableAuthorizedExecution:
    evidence = tuple(_evidence_id(offer) for offer in offers)
    currencies = tuple(offer.source.currency for offer in offers)
    amounts = tuple(offer.source.price_amount_minor for offer in offers)
    state = _state_for(outcome)
    trace = _trace(
        attempt,
        started_at=execution.attempt_started_at or attempt.now,
        finished_at=finished_at,
        attempt_status=attempt_status,
        error_category=error_category,
        evidence_ids=evidence,
    )
    return replace(
        execution,
        state=state,
        updated_at=finished_at,
        finished_at=finished_at,
        claimed_at=None,
        claim_expires_at=None,
        claim_digest=None,
        outcome=outcome,
        error_category=error_category,
        evaluated_offer_count=len(offers),
        normalized_offer_count=len(offers),
        returned_currencies=currencies,
        normalized_amount_minors=amounts,
        evidence_ids=evidence,
        observation_kind=observation_kind,
        request_digest=request_digest,
        trace=trace,
        raw_response_persisted=False,
    )


def _state_for(outcome: str) -> Literal["completed", "failed", "outcome_unknown"]:
    if outcome == "succeeded":
        return "completed"
    if outcome == "outcome_unknown":
        return "outcome_unknown"
    return "failed"


def _trace(
    attempt: ShopifyCatalogAttempt,
    *,
    started_at: datetime,
    finished_at: datetime,
    attempt_status: str,
    error_category: str | None,
    evidence_ids: tuple[str, ...],
) -> ResearchExecutionTrace:
    source = attempt.source
    step = ResearchExecutionTraceStep(
        plan_id=attempt.plan.plan_id,
        provider_id=attempt.step.provider_id,
        requested_capability=attempt.step.capability,
        market=attempt.step.market,
        source=source,
        attempted=True,
        attempt_status=attempt_status,  # type: ignore[arg-type]
        evidence_ids=evidence_ids,
        started_at=started_at,
        finished_at=finished_at,
        error_category=error_category,
        evaluated_offer_count=len(evidence_ids),
        freshness_checked_at=None,
    )
    return ResearchExecutionTrace(
        plan_id=attempt.plan.plan_id,
        steps=(step,),
        attempted_sources=(source,),
        succeeded_sources=(source,) if attempt_status == "succeeded" else (),
        failed_sources=(source,) if attempt_status == "failed" else (),
        timed_out_sources=(source,) if attempt_status == "timed_out" else (),
        evaluated_offer_count=len(evidence_ids),
    )


def _evidence_id(offer: ShopifyNormalizedOffer) -> str:
    return stable_sha256(
        {
            "kind": "shopify_normalized_offer_v1",
            "product_id": offer.source.product_id,
            "variant_id": offer.source.variant_id,
            "currency": offer.source.currency,
            "amount_minor": offer.source.price_amount_minor,
            "seller": offer.source.seller_identity,
        }
    )


def _unknown_costs(offers: tuple[ShopifyNormalizedOffer, ...]) -> tuple[str, ...]:
    if not offers:
        return ()
    for offer in offers:
        economics = offer.economics
        lines = (economics.shipping, economics.taxes, economics.import_charges, economics.voucher)
        if any(line.amount_minor is not None or line.status != "unknown" for line in lines):
            return ()
        if offer.economics.price_state == "final_effective_cost":
            return ()
    return _UNKNOWN_COSTS


def _same_step(left: ResearchProviderStep, right: ResearchProviderStep) -> bool:
    return (
        left.step_index == right.step_index
        and left.provider_id == right.provider_id
        and left.capability == right.capability
        and left.market == right.market
        and left.source_identities == right.source_identities
        and left.certification_id == right.certification_id
        and left.certification_version == right.certification_version
    )


def _from_stored(
    stored: DurableAuthorizedExecution,
    *,
    transport_invoked: bool,
    failure_kind: ConnectorFailureKind | None = None,
    unknown_costs: tuple[str, ...] = (),
) -> ShopifyExecutionResult:
    return ShopifyExecutionResult(
        attempted=True,
        transport_invoked=transport_invoked,
        persisted=True,
        state=stored.state,
        block_reason=None,
        outcome=stored.outcome,
        error_category=stored.error_category,
        failure_kind=None if failure_kind is None else failure_kind.value,
        evaluated_offer_count=stored.evaluated_offer_count,
        normalized_offer_count=stored.normalized_offer_count,
        returned_currencies=stored.returned_currencies,
        observation_kind=stored.observation_kind,
        claim_released=stored.claim_digest is None,
        trace=stored.trace,
        unknown_cost_components=unknown_costs,
    )


def _refused(
    reason: str,
    *,
    attempted: bool = False,
    transport_invoked: bool = False,
    state: str | None = None,
    blocking_reasons: tuple[str, ...] = (),
    transport_outcome_ambiguous: bool = False,
) -> ShopifyExecutionResult:
    return ShopifyExecutionResult(
        attempted=attempted,
        transport_invoked=transport_invoked,
        persisted=False,
        state=state,
        block_reason=reason,
        blocking_reasons=blocking_reasons or (reason,),
        transport_outcome_ambiguous=transport_outcome_ambiguous,
    )
