"""Non-authoritative Shopify reliability candidate.

Reuses Sprint 31 operational and failure contracts. It does not register a
production provider, certify Shopify, or perform HTTP. Synthetic failure
classifications are not live operational evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.entities.connector_reliability import (
    BoundedRetryPolicy,
    CircuitBreakerSnapshot,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    ExponentialBackoffPolicy,
    KillSwitch,
    PartialFailure,
    QuotaFailure,
    TimeoutPolicy,
)
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.marketplace.normalization.shopify_global_catalog import (
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
    ShopifyNormalizationRefusal,
)
from app.research.providers import StaticResearchProvider
from app.research.shopify_global_catalog_ph_probe import (
    ProbeResponseError,
    products_from_catalog_payload,
    validate_catalog_tool_response,
)

# Distinct from the documentary evidence provider id. Not production-registered.
SHOPIFY_NORMALIZATION_CANDIDATE_ID = "ph-shopify-global-catalog-normalization-candidate"
CANDIDATE_AUTHORITATIVE = False
CANDIDATE_PRODUCTION_CERTIFIED = False
_SUPPORTED_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.AVAILABILITY,
)


@dataclass(frozen=True, slots=True)
class ShopifyReliabilityCandidate:
    """In-memory candidate profile. Not a production registry row."""

    authoritative: bool
    production_certified: bool
    registered_in_production_registry: bool
    live_operational_evidence: bool
    descriptor: ResearchProviderDescriptor
    timeout_policy: TimeoutPolicy
    retry_policy: BoundedRetryPolicy
    backoff_policy: ExponentialBackoffPolicy

    def __post_init__(self) -> None:
        registered = self.registered_in_production_registry
        if self.authoritative or self.production_certified or registered:
            raise ValueError("this Shopify candidate is not production authority")
        if self.live_operational_evidence:
            raise ValueError("synthetic reliability checks are not live operational evidence")
        if self.descriptor.provider_id != SHOPIFY_NORMALIZATION_CANDIDATE_ID:
            raise ValueError("candidate provider id must stay non-authoritative")
        if self.descriptor.test_fixture:
            raise ValueError("candidate descriptor is not a test-fixture provider type")


@dataclass(frozen=True, slots=True)
class ShopifyFailClosedClassification:
    """Failure-mode result. Usable offers stay false when the path fails closed."""

    fail_closed: bool
    usable_offer: bool
    live_operational_evidence: bool
    reason: str
    failure_kind: ConnectorFailureKind | None = None
    quota: QuotaFailure | None = None
    partial: PartialFailure | None = None

    def __post_init__(self) -> None:
        if self.live_operational_evidence:
            raise ValueError("synthetic failure classification is not live evidence")
        if self.fail_closed and self.usable_offer:
            raise ValueError("a fail-closed result must not yield a usable offer")


def shopify_normalization_reliability_candidate(
    *,
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    kill_switch: KillSwitch | None = None,
    circuit_breaker: CircuitBreakerSnapshot | None = None,
) -> ShopifyReliabilityCandidate:
    """Build a non-authoritative candidate. Does not register or certify it."""

    descriptor = ResearchProviderDescriptor(
        provider_id=SHOPIFY_NORMALIZATION_CANDIDATE_ID,
        provider_type="merchant",
        supported_markets=("PH",),
        supported_capabilities=_SUPPORTED_CAPABILITIES,
        supported_sources=(SHOPIFY_GLOBAL_CATALOG_SOURCE,),
        operational_status=operational_status,
        test_fixture=False,
        kill_switch=kill_switch or KillSwitch(engaged=False),
        circuit_breaker=circuit_breaker or CircuitBreakerSnapshot(),
        affiliate_commission_rate=None,
        may_expand_evaluated_set=False,
        can_provide_pricing=True,
        can_provide_shipping_taxes=False,
        can_provide_product_evidence=True,
        can_provide_review_evidence=False,
    )
    return ShopifyReliabilityCandidate(
        authoritative=CANDIDATE_AUTHORITATIVE,
        production_certified=CANDIDATE_PRODUCTION_CERTIFIED,
        registered_in_production_registry=False,
        live_operational_evidence=False,
        descriptor=descriptor,
        timeout_policy=TimeoutPolicy(timeout_ms=5_000),
        retry_policy=BoundedRetryPolicy(max_attempts=1, retry_on=()),
        backoff_policy=ExponentialBackoffPolicy(),
    )


def shopify_candidate_is_available(
    descriptor: ResearchProviderDescriptor,
    *,
    browser_disengage_kill_switch: bool = False,
    request_disengage_kill_switch: bool = False,
    shopper_disengage_kill_switch: bool = False,
) -> bool:
    """Server-owned operational predicate. Caller input cannot disengage a kill switch."""

    del browser_disengage_kill_switch, request_disengage_kill_switch, shopper_disengage_kill_switch
    return descriptor.is_operationally_available


def shopify_candidate_eligibility(descriptor: ResearchProviderDescriptor) -> tuple[str, ...]:
    """Sprint 31 technical eligibility reasons for the candidate descriptor."""

    eligibility = StaticResearchProvider(descriptor).supports(
        ResearchCapability.CURRENT_PRICING,
        "PH",
        SHOPIFY_GLOBAL_CATALOG_SOURCE,
    )
    return eligibility.reasons if not eligibility.eligible else ()


def classify_shopify_synthetic_timeout(
    *,
    elapsed_ms: int,
    policy: TimeoutPolicy,
) -> ShopifyFailClosedClassification:
    """Classify a synthetic timeout. Does not call Shopify or sleep."""

    if elapsed_ms >= policy.timeout_ms:
        return _closed(
            "timeout",
            ConnectorFailureKind.TIMEOUT,
        )
    return ShopifyFailClosedClassification(
        fail_closed=False,
        usable_offer=False,
        live_operational_evidence=False,
        reason="within_timeout",
        failure_kind=None,
    )


def classify_shopify_synthetic_quota(
    *, rate_limit: bool = False
) -> ShopifyFailClosedClassification:
    """Classify a synthetic quota or rate-limit result. Does not trigger one."""

    kind = ConnectorFailureKind.RATE_LIMIT if rate_limit else ConnectorFailureKind.QUOTA
    quota = QuotaFailure(kind=kind, retryable=False, message="synthetic shopify quota")
    return ShopifyFailClosedClassification(
        fail_closed=True,
        usable_offer=False,
        live_operational_evidence=False,
        reason="quota",
        failure_kind=kind,
        quota=quota,
    )


def classify_shopify_synthetic_partial() -> ShopifyFailClosedClassification:
    """Classify a synthetic partial catalog result. Not live evidence."""

    partial = PartialFailure(
        kind=ConnectorFailureKind.PARTIAL,
        retryable=False,
        completed_capabilities=("product_discovery",),
        missing_capabilities=("current_pricing",),
        message="synthetic partial shopify catalog response",
    )
    return ShopifyFailClosedClassification(
        fail_closed=True,
        usable_offer=False,
        live_operational_evidence=False,
        reason="partial_response",
        failure_kind=ConnectorFailureKind.PARTIAL,
        partial=partial,
    )


def classify_shopify_catalog_envelope(payload: Any) -> ShopifyFailClosedClassification:
    """Fail closed on malformed, JSON-RPC, MCP, or partial catalog envelopes."""

    if not isinstance(payload, dict):
        return _closed("malformed_jsonrpc", ConnectorFailureKind.UNKNOWN)
    if payload.get("error") is not None:
        return _closed("jsonrpc_error", ConnectorFailureKind.UNAVAILABLE)
    result = payload.get("result")
    if isinstance(result, dict) and result.get("isError") is True:
        return _closed("mcp_is_error", ConnectorFailureKind.UNAVAILABLE)
    try:
        validate_catalog_tool_response(payload)
        products = products_from_catalog_payload(payload)
    except ProbeResponseError:
        return _closed("malformed_jsonrpc", ConnectorFailureKind.UNKNOWN)
    if not products:
        return classify_shopify_synthetic_partial()
    return ShopifyFailClosedClassification(
        fail_closed=False,
        usable_offer=False,
        live_operational_evidence=False,
        reason="envelope_accepted",
        failure_kind=None,
    )


def classify_shopify_normalization_refusal(
    refusal: ShopifyNormalizationRefusal,
) -> ShopifyFailClosedClassification:
    """Map a normalization refusal to a fail-closed reliability result."""

    return _closed(refusal.reason, ConnectorFailureKind.PARTIAL)


def classify_conflicting_variant_identity(
    left_variant_id: str,
    right_variant_id: str,
) -> ShopifyFailClosedClassification:
    """Distinct source variant ids must not collapse into one usable offer."""

    if left_variant_id and right_variant_id and left_variant_id != right_variant_id:
        return _closed("conflicting_variant_identity", ConnectorFailureKind.PARTIAL)
    return ShopifyFailClosedClassification(
        fail_closed=False,
        usable_offer=False,
        live_operational_evidence=False,
        reason="variant_identity_not_conflicting",
        failure_kind=None,
    )


def _closed(reason: str, kind: ConnectorFailureKind) -> ShopifyFailClosedClassification:
    return ShopifyFailClosedClassification(
        fail_closed=True,
        usable_offer=False,
        live_operational_evidence=False,
        reason=reason,
        failure_kind=kind,
    )
