"""Sprint 32 Shopify canonical normalization, identity, and reliability."""

from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerSnapshot,
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.decision_snapshot import AffiliateNeutralitySnapshot
from app.domain.entities.marketplace_data import ProductAvailability, SourceMode
from app.domain.entities.product_match import MatchType
from app.domain.entities.research_certification_decision import CertificationDecisionRequest
from app.marketplace.normalization.shopify_global_catalog import (
    RETAINED_SHOPPER_FACING_FRESHNESS_ESTABLISHED,
    ShopifyNormalizationRefusal,
    compare_shopify_variant_identity,
    compose_shopify_match_title,
    normalize_shopify_global_catalog_offer,
)
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_capability_policy import shopify_capability_policy_index
from app.research.shopify_global_catalog_normalization_harness import (
    EXACT_DEPLOYED_STAGING_CLASSIFICATION,
    MAX_GET_PRODUCT_CALLS,
    MAX_SEARCH_CATALOG_CALLS,
    OWNER_HARNESS_USER_AGENT,
    OWNER_LIVE_HARNESS_RUN_BY_CURSOR,
    OWNER_NORMALIZATION_CATEGORIES,
    ShopifyNormalizationHarnessBudget,
    ShopifyNormalizationHarnessError,
    _assert_request_in_bounds,
    assert_owner_harness_profile,
    run_shopify_normalization_validation,
    stable_source_digest,
    staging_normalization_profile,
    write_normalization_summary,
)
from app.research.shopify_global_catalog_ph_probe import (
    ANONYMOUS_USER_AGENT,
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    SEARCH_TOOL,
    build_get_product_arguments,
    build_search_catalog_arguments,
)
from app.research.shopify_global_catalog_reliability import (
    SHOPIFY_NORMALIZATION_CANDIDATE_ID,
    classify_conflicting_variant_identity,
    classify_shopify_catalog_envelope,
    classify_shopify_normalization_refusal,
    classify_shopify_synthetic_partial,
    classify_shopify_synthetic_quota,
    classify_shopify_synthetic_timeout,
    shopify_candidate_eligibility,
    shopify_candidate_is_available,
    shopify_normalization_reliability_candidate,
)
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)
from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
)
from scripts.shopify_global_catalog_normalization_validation import main as harness_main

from tests.unit.production_catalog_boundaries import assert_production_shopify_evidence_only

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
CHECKED = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
RAW_SENTINEL = "RAW_SHOPIFY_DESCRIPTION_SENTINEL"
RETURNED_PAGE_CURSOR = "shopify-returned-next-cursor"


def _variant(
    *,
    variant_id: str = "gid://shopify/ProductVariant/earbuds-black",
    title: str | None = None,
    amount: int | str | float | bool | None = 249900,
    currency: str | None = "PHP",
    seller: str | None = "North Audio",
    source_timestamp: str | None = None,
    include_price: bool = True,
) -> dict:
    variant: dict = {
        "id": variant_id,
        "checkout_url": "https://north-audio.merchant.test/cart/1",
        "availability": {"available": True, "status": "in_stock"},
        "seller": {
            "name": seller,
            "id": "shop-north",
            "domain": "north-audio.merchant.test",
            "url": "https://north-audio.merchant.test",
        },
    }
    if title is not None:
        variant["title"] = title
    if include_price:
        price: dict = {}
        if amount is not None:
            price["amount"] = amount
        if currency is not None:
            price["currency"] = currency
        variant["price"] = price
    if source_timestamp is not None:
        variant["source_timestamp"] = source_timestamp
    return variant


def _product(
    variant: dict | None = None,
    *,
    product_id: str = "gid://shopify/p/earbuds-1",
    title: str = "Apple iPhone 17 Pro Max 256GB Black Titanium",
    variants: list | None = None,
) -> tuple[dict, dict]:
    chosen = variant if variant is not None else _variant()
    product = {
        "id": product_id,
        "title": title,
        "url": "https://north-audio.merchant.test/products/item",
        "description": {"html": RAW_SENTINEL},
        "media": [{"url": "https://cdn.merchant.test/image.jpg"}],
        "metadata": {"top_features": ["inferred feature"]},
        "shipping_cost": 0,
        "tax": 0,
        "voucher": {"amount": 500, "applied": True},
        "seller_discount": 100,
        "platform_discount": 50,
        "checkout_fee": 25,
        "variants": variants if variants is not None else [chosen],
    }
    return product, chosen


def _offer(**kwargs):
    product_kwargs = {}
    variant_kwargs = {}
    observation_kind = kwargs.pop("observation_kind", "synthetic")
    checked_at = kwargs.pop("checked_at", CHECKED)
    ph_query_context = kwargs.pop("ph_query_context", True)
    explicit_variant = kwargs.pop("explicit_variant", True)
    for key in ("product_id", "title"):
        if key in kwargs:
            product_kwargs[key] = kwargs.pop(key)
    if "variants" in kwargs:
        product_kwargs["variants"] = kwargs.pop("variants")
    if "variant_title" in kwargs:
        variant_kwargs["title"] = kwargs.pop("variant_title")
    variant_kwargs.update(kwargs)
    product, variant = _product(_variant(**variant_kwargs), **product_kwargs)
    return normalize_shopify_global_catalog_offer(
        product,
        variant if explicit_variant else None,
        checked_at=checked_at,
        observation_kind=observation_kind,
        ph_query_context=ph_query_context,
    )


def _envelope(product: dict, *, pagination: dict | None = None) -> dict:
    content: dict = {"products": [product]}
    if pagination is not None:
        content["pagination"] = pagination
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"isError": False, "structuredContent": content},
    }


def _catalog_product(
    *,
    product_id: str,
    title: str,
    amount: int,
    currency: str,
    variants: list[dict] | None = None,
) -> dict:
    chosen = variants or [
        _variant(
            variant_id=f"{product_id}-v1",
            amount=amount,
            currency=currency,
            seller="North Audio",
        )
    ]
    product, _variant_ignored = _product(
        chosen[0],
        product_id=product_id,
        title=title,
        variants=chosen,
    )
    return product


class MemoryTransport:
    def __init__(
        self,
        by_query: dict[str, dict],
        by_id: dict[str, dict],
        *,
        search_override: dict | None = None,
        detail_override=None,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.by_query = by_query
        self.by_id = by_id
        self.search_override = search_override
        self.detail_override = detail_override

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        if name == FORBIDDEN_LOOKUP_TOOL:
            raise AssertionError("lookup_catalog was called")
        if name == "search_catalog":
            if self.search_override is not None:
                return self.search_override
            return self.by_query[arguments["catalog"]["query"]]
        if name == "get_product":
            if self.detail_override is not None:
                return self.detail_override(arguments)
            return self.by_id[arguments["catalog"]["id"]]
        raise AssertionError(name)


def _diversified_transport() -> MemoryTransport:
    specs = (
        ("wireless earbuds", "gid://shopify/p/norm-earbuds", "Wireless earbuds", 10001, "PHP"),
        ("gaming laptop", "gid://shopify/p/norm-laptop", "Gaming laptop", 20002, "USD"),
        ("USB-C charger", "gid://shopify/p/norm-charger", "USB-C charger", 30003, "INR"),
        ("phone case", "gid://shopify/p/norm-case", "Phone case", 40004, "JPY"),
    )
    by_query: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for query, product_id, title, amount, currency in specs:
        product = _catalog_product(
            product_id=product_id,
            title=title,
            amount=amount,
            currency=currency,
        )
        envelope = _envelope(
            product,
            pagination={"has_next_page": True, "cursor": RETURNED_PAGE_CURSOR, "page": 2},
        )
        by_query[query] = envelope
        by_id[product_id] = envelope
    keyboard_variants = [
        _variant(
            variant_id="gid://shopify/ProductVariant/keyboard-red",
            amount=8999,
            currency="EUR",
        ),
        _variant(
            variant_id="gid://shopify/ProductVariant/keyboard-blue",
            amount=8999,
            currency="EUR",
        ),
    ]
    keyboard = _catalog_product(
        product_id="gid://shopify/p/norm-keyboard",
        title="Mechanical keyboard",
        amount=8999,
        currency="EUR",
        variants=keyboard_variants,
    )
    keyboard_envelope = _envelope(
        keyboard,
        pagination={"has_next_page": True, "cursor": RETURNED_PAGE_CURSOR, "page": 2},
    )
    by_query["mechanical keyboard"] = keyboard_envelope
    by_id["gid://shopify/p/norm-keyboard"] = keyboard_envelope
    return MemoryTransport(by_query, by_id)


def test_shopify_product_id_is_preserved() -> None:
    offer = _offer(product_id="gid://shopify/p/preserved-product")
    assert offer.source.product_id == "gid://shopify/p/preserved-product"
    assert offer.source.source_identity == "shopify_global_catalog"
    assert offer.parsed.model != offer.source.product_id
    assert offer.economics.product_id == offer.source.product_id


def test_shopify_variant_id_is_preserved() -> None:
    offer = _offer(variant_id="gid://shopify/ProductVariant/preserved-variant")
    assert offer.source.variant_id == "gid://shopify/ProductVariant/preserved-variant"
    assert offer.parsed.storage != offer.source.variant_id


def test_distinct_variant_ids_do_not_silently_merge() -> None:
    title = "Apple iPhone 17 Pro Max 256GB Black Titanium"
    left = _offer(variant_id="gid://shopify/ProductVariant/a", title=title)
    right = _offer(variant_id="gid://shopify/ProductVariant/b", title=title)
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.source_variant_ids_conflict is True
    assert decision.title_similarity_overridden is True
    assert decision.relation == "different_source_variant"
    assert decision.parsed_match.match_type == MatchType.EXACT_VARIANT


def test_storage_conflict_remains_different_variant() -> None:
    left = _offer(title="Apple iPhone 17 Pro Max 256GB Black Titanium", variant_id="v-256")
    right = _offer(title="Apple iPhone 17 Pro Max 512GB Black Titanium", variant_id="v-512")
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.parsed_match.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(conflict.field == "storage" for conflict in decision.parsed_match.conflicts)


def test_color_conflict_remains_different_variant() -> None:
    left = _offer(title="Apple iPhone 17 Pro Max 256GB Black Titanium", variant_id="v-black")
    right = _offer(title="Apple iPhone 17 Pro Max 256GB White Titanium", variant_id="v-white")
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.parsed_match.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(conflict.field == "color" for conflict in decision.parsed_match.conflicts)


def test_connector_conflict_remains_different_variant() -> None:
    left = _offer(title="AirPods Pro 2 USB-C", variant_id="v-usbc")
    right = _offer(title="AirPods Pro 2 Lightning", variant_id="v-lightning")
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.parsed_match.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(conflict.field == "connector" for conflict in decision.parsed_match.conflicts)


def test_model_conflict_remains_different_product() -> None:
    left = _offer(
        title="Apple iPhone 17 Pro 256GB",
        product_id="gid://shopify/p/pro",
        variant_id="v-pro",
    )
    right = _offer(
        title="Apple iPhone 17 Pro Max 256GB",
        product_id="gid://shopify/p/pro-max",
        variant_id="v-pro-max",
    )
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.relation == "different_product"
    assert decision.parsed_match.match_type == MatchType.DIFFERENT_PRODUCT
    assert any(conflict.field == "model" for conflict in decision.parsed_match.conflicts)


def test_insufficient_title_identity_is_not_an_exact_match() -> None:
    left = _offer(title="mystery gadget", variant_id="v-1")
    right = _offer(title="another unknown thing", variant_id="v-2")
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.parsed_match.is_match is False
    assert decision.parsed_match.match_type == MatchType.INSUFFICIENT_INFORMATION
    assert decision.relation in {"different_source_variant", "insufficient_information"}
    assert decision.parsed_match.match_type != MatchType.EXACT_VARIANT


def test_generic_title_does_not_merge_distinct_variants() -> None:
    left = _offer(title="Phone Case", variant_id="gid://shopify/ProductVariant/case-a")
    right = _offer(title="Phone Case", variant_id="gid://shopify/ProductVariant/case-b")
    decision = compare_shopify_variant_identity(left, right)
    assert decision.merged is False
    assert decision.source_variant_ids_conflict is True
    assert decision.parsed_match.match_type != MatchType.EXACT_VARIANT


def test_match_title_composition_is_deterministic() -> None:
    assert (
        compose_shopify_match_title("Apple iPhone 17 Pro Max", "256GB Black Titanium")
        == "Apple iPhone 17 Pro Max — 256GB Black Titanium"
    )
    assert compose_shopify_match_title("Widget", "Default Title") == "Widget"
    assert compose_shopify_match_title("Widget", "Widget") == "Widget"
    assert compose_shopify_match_title("Widget", None) == "Widget"
    offer = _offer(title="USB-C charger", variant_title="65W")
    assert offer.match_title == "USB-C charger — 65W"
    assert offer.source.product_title == "USB-C charger"
    assert offer.source.variant_title == "65W"


def test_parser_does_not_invent_identity_from_non_title_fields() -> None:
    offer = _offer(title="Wireless earbuds", seller="Apple Official Store")
    assert offer.parsed.brand is None
    assert offer.parsed.model is None
    assert offer.parsed.storage is None
    assert offer.source.seller_identity == "Apple Official Store"


def test_integer_price_amount_minor_is_preserved_exactly() -> None:
    offer = _offer(amount=249900)
    assert offer.source.price_amount_minor == 249900
    assert offer.economics.listing.amount_minor == 249900
    assert offer.economics.dominant_amount_minor == 249900
    assert type(offer.economics.listing.amount_minor) is int
    large = _offer(amount=10**18, currency="JPY")
    assert large.source.price_amount_minor == 10**18
    assert large.economics.listing.amount_minor == 10**18
    string_amount = _offer(amount="249900")
    assert string_amount.source.price_amount_minor == 249900
    product, variant = _product(_variant(amount=10.5))
    with pytest.raises(ShopifyNormalizationRefusal, match="missing_price"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)


def test_returned_currency_is_preserved_exactly() -> None:
    offer = _offer(currency="usd", ph_query_context=True)
    assert offer.source.currency == "USD"
    assert offer.economics.currency == "USD"
    assert offer.economics.listing.currency == "USD"
    assert offer.economics.shipping.currency == "USD"


def test_mixed_currencies_are_not_rewritten_to_php() -> None:
    usd = _offer(currency="USD", amount=1500, ph_query_context=True)
    inr = _offer(currency="INR", amount=8800, ph_query_context=True)
    jpy = _offer(currency="JPY", amount=1980, ph_query_context=True)
    assert {usd.source.currency, inr.source.currency, jpy.source.currency} == {"USD", "INR", "JPY"}
    assert "PHP" not in {usd.source.currency, inr.source.currency, jpy.source.currency}
    assert jpy.economics.listing.amount_minor == 1980


def test_absent_shipping_is_unknown_not_zero() -> None:
    offer = _offer()
    assert offer.economics.shipping.status == "unknown"
    assert offer.economics.shipping.amount_minor is None
    assert offer.economics.shipping.applied is False
    assert offer.free_shipping_claimed is False
    assert "shipping unknown" in offer.economics.unknowns
    assert "free shipping unknown" in offer.economics.unknowns


def test_absent_tax_is_unknown_not_zero() -> None:
    offer = _offer()
    assert offer.economics.taxes.status == "unknown"
    assert offer.economics.taxes.amount_minor is None
    assert offer.economics.import_charges is not None
    assert offer.economics.import_charges.amount_minor is None
    assert offer.economics.import_charges.status == "unknown"
    assert "taxes unknown" in offer.economics.unknowns
    assert "import charges unknown" in offer.economics.unknowns


def test_absent_voucher_is_not_applied() -> None:
    offer = _offer()
    assert offer.voucher_applied is False
    assert offer.seller_discount_applied is False
    assert offer.platform_discount_applied is False
    assert offer.economics.voucher is not None
    assert offer.economics.voucher.applied is False
    assert offer.economics.voucher.amount_minor is None
    assert offer.economics.voucher.status == "unknown"
    assert offer.economics.dominant_amount_minor == offer.source.price_amount_minor
    assert "voucher not applied" in offer.economics.unknowns
    assert "voucher eligibility unknown" in offer.economics.unknowns


def test_absent_checkout_costs_are_unknown() -> None:
    offer = _offer()
    assert offer.checkout_cost_amount_minor is None
    assert "checkout costs unknown" in offer.economics.unknowns


def test_effective_price_is_not_final_when_costs_are_unknown() -> None:
    offer = _offer()
    assert offer.economics.price_state == "price_before_shipping"
    assert offer.economics.price_state != "final_effective_cost"
    assert offer.economics.dominant_amount_minor == offer.economics.listing.amount_minor


def test_checked_at_is_distinct_from_provider_timestamp() -> None:
    provider_time = "2026-09-01T00:00:00Z"
    offer = _offer(source_timestamp=provider_time)
    assert offer.provenance.observed_at == CHECKED
    assert offer.economics.checked_at == CHECKED
    assert offer.source.provider_source_timestamp == datetime(2026, 9, 1, tzinfo=UTC)
    assert offer.provenance.source_timestamp != offer.provenance.observed_at
    assert offer.source.provider_timestamp_supplied is True
    assert offer.retained_shopper_facing_freshness_established is False
    assert RETAINED_SHOPPER_FACING_FRESHNESS_ESTABLISHED is False
    assert offer.freshness.is_current_live_price is False
    assert offer.freshness.status.value == "unknown"
    assert offer.economics.freshness == "unknown"


def test_absent_provider_timestamp_is_not_fabricated() -> None:
    offer = _offer(observation_kind="live")
    assert offer.source.provider_source_timestamp is None
    assert offer.source.provider_timestamp_supplied is False
    assert offer.provenance.source_timestamp is None
    assert offer.provenance.observed_at == CHECKED
    assert offer.provenance.source_timestamp != offer.provenance.observed_at
    assert offer.economics.freshness == "unknown"
    assert offer.freshness.is_current_live_price is False
    assert "did not supply a freshness timestamp" in (offer.freshness.warning or "")
    assert offer.retained_shopper_facing_freshness_established is False


def test_fixture_and_synthetic_records_are_not_labeled_live() -> None:
    synthetic = _offer(observation_kind="synthetic")
    fixture = _offer(observation_kind="fixture")
    assert synthetic.source.source_mode == SourceMode.FIXTURE
    assert fixture.source.source_mode == SourceMode.FIXTURE
    assert synthetic.provenance.source_mode != SourceMode.LIVE
    assert fixture.freshness.is_current_live_price is False
    assert "not live" in synthetic.provenance.notes


def test_raw_response_is_not_persisted() -> None:
    product, variant = _product()
    offer = normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)
    blob = json.dumps(offer, default=lambda item: getattr(item, "__dict__", str(item)))
    assert RAW_SENTINEL not in blob
    assert "top_features" not in blob
    assert offer.raw_response_persisted is False
    assert offer.source.raw_response_persisted is False
    assert not hasattr(offer, "raw_payload")


def test_placeholder_or_test_record_is_rejected() -> None:
    product, variant = _product()
    product["url"] = "https://example.com/products/placeholder"
    with pytest.raises(ShopifyNormalizationRefusal, match="placeholder_or_test"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)
    refusal = ShopifyNormalizationRefusal("placeholder_or_test")
    classified = classify_shopify_normalization_refusal(refusal)
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.live_operational_evidence is False


def test_missing_seller_fails_useful_normalization() -> None:
    product, variant = _product(_variant(seller=None))
    variant["seller"] = {}
    with pytest.raises(ShopifyNormalizationRefusal, match="missing_seller_identity"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)


def test_missing_price_fails_useful_normalization() -> None:
    product, variant = _product(_variant(include_price=False))
    with pytest.raises(ShopifyNormalizationRefusal, match="missing_price"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)


def test_missing_currency_fails_useful_normalization() -> None:
    product, variant = _product(_variant(currency=None))
    with pytest.raises(ShopifyNormalizationRefusal, match="missing_currency"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)


def test_missing_product_identity_fails_closed() -> None:
    product, variant = _product()
    product["id"] = "  "
    with pytest.raises(ShopifyNormalizationRefusal, match="missing_product_identity"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)


def test_conflicting_variant_identity_fails_closed() -> None:
    product, variant = _product()
    variant["variant_id"] = "gid://shopify/ProductVariant/other"
    with pytest.raises(ShopifyNormalizationRefusal, match="conflicting_variant_identity"):
        normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)
    first = _variant(variant_id="gid://shopify/ProductVariant/one")
    second = _variant(variant_id="gid://shopify/ProductVariant/two")
    many, _ignored = _product(variants=[first, second])
    with pytest.raises(ShopifyNormalizationRefusal, match="conflicting_variant_identity"):
        normalize_shopify_global_catalog_offer(many, checked_at=CHECKED)
    classified = classify_conflicting_variant_identity(
        "gid://shopify/ProductVariant/one",
        "gid://shopify/ProductVariant/two",
    )
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.reason == "conflicting_variant_identity"
    assert classified.live_operational_evidence is False


def test_normal_candidate_can_be_technically_available() -> None:
    candidate = shopify_normalization_reliability_candidate()
    assert candidate.authoritative is False
    assert candidate.production_certified is False
    assert candidate.registered_in_production_registry is False
    assert candidate.live_operational_evidence is False
    assert candidate.descriptor.is_operationally_available is True
    assert candidate.descriptor.affiliate_commission_rate is None
    assert candidate.retry_policy.max_attempts == 1
    assert shopify_candidate_eligibility(candidate.descriptor) == ()
    assert production_research_provider_registry().get(SHOPIFY_NORMALIZATION_CANDIDATE_ID) is None


def test_engaged_kill_switch_blocks_candidate() -> None:
    candidate = shopify_normalization_reliability_candidate(
        kill_switch=KillSwitch(engaged=True, reason="server-owned")
    )
    assert candidate.descriptor.is_operationally_available is False
    assert (
        shopify_candidate_is_available(
            candidate.descriptor,
            browser_disengage_kill_switch=True,
            request_disengage_kill_switch=True,
            shopper_disengage_kill_switch=True,
        )
        is False
    )
    assert "kill_switch" in shopify_candidate_eligibility(candidate.descriptor)


def test_open_circuit_breaker_blocks_candidate() -> None:
    candidate = shopify_normalization_reliability_candidate(
        circuit_breaker=CircuitBreakerSnapshot(state=CircuitBreakerState.OPEN, reason="synthetic")
    )
    assert candidate.descriptor.circuit_breaker.allows_execution is False
    assert candidate.descriptor.is_operationally_available is False
    assert "circuit_open" in shopify_candidate_eligibility(candidate.descriptor)


def test_disabled_provider_blocks_candidate() -> None:
    candidate = shopify_normalization_reliability_candidate(
        operational_status=ConnectorOperationalStatus.DISABLED
    )
    assert candidate.descriptor.is_operationally_available is False
    assert "provider_unavailable" in shopify_candidate_eligibility(candidate.descriptor)


def test_unavailable_provider_blocks_candidate() -> None:
    candidate = shopify_normalization_reliability_candidate(
        operational_status=ConnectorOperationalStatus.UNAVAILABLE
    )
    assert candidate.descriptor.is_operationally_available is False
    assert "provider_unavailable" in shopify_candidate_eligibility(candidate.descriptor)


def test_synthetic_timeout_is_fail_closed_and_not_live_evidence() -> None:
    candidate = shopify_normalization_reliability_candidate()
    classified = classify_shopify_synthetic_timeout(
        elapsed_ms=5_000,
        policy=candidate.timeout_policy,
    )
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.live_operational_evidence is False
    assert classified.failure_kind == ConnectorFailureKind.TIMEOUT
    within = classify_shopify_synthetic_timeout(elapsed_ms=4_999, policy=candidate.timeout_policy)
    assert within.fail_closed is False
    assert within.live_operational_evidence is False


def test_synthetic_quota_and_rate_limit_are_fail_closed() -> None:
    quota = classify_shopify_synthetic_quota()
    limited = classify_shopify_synthetic_quota(rate_limit=True)
    assert quota.fail_closed is True
    assert quota.usable_offer is False
    assert quota.live_operational_evidence is False
    assert quota.failure_kind == ConnectorFailureKind.QUOTA
    assert quota.quota is not None
    assert limited.failure_kind == ConnectorFailureKind.RATE_LIMIT
    assert limited.quota is not None
    assert limited.quota.retryable is False


def test_synthetic_partial_response_is_fail_closed() -> None:
    classified = classify_shopify_synthetic_partial()
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.live_operational_evidence is False
    assert classified.failure_kind == ConnectorFailureKind.PARTIAL
    assert classified.partial is not None
    assert "current_pricing" in classified.partial.missing_capabilities


def test_jsonrpc_error_fails_closed() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32001, "message": "UCP discovery failed"},
    }
    classified = classify_shopify_catalog_envelope(payload)
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.reason == "jsonrpc_error"
    assert classified.live_operational_evidence is False


def test_mcp_is_error_fails_closed() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "isError": True,
            "structuredContent": {"messages": [{"code": "bad", "content": "nope"}]},
        },
    }
    classified = classify_shopify_catalog_envelope(payload)
    assert classified.fail_closed is True
    assert classified.usable_offer is False
    assert classified.reason == "mcp_is_error"
    malformed = classify_shopify_catalog_envelope(["not", "an", "object"])
    assert malformed.fail_closed is True
    assert malformed.reason == "malformed_jsonrpc"


def test_owner_harness_budgets_are_five_search_and_five_get_product() -> None:
    assert MAX_SEARCH_CATALOG_CALLS == 5
    assert MAX_GET_PRODUCT_CALLS == 5
    assert len(OWNER_NORMALIZATION_CATEGORIES) == 5
    assert OWNER_HARNESS_USER_AGENT == "PiqSavi-Sprint32-PH-Coverage-Probe/1.0"
    assert OWNER_HARNESS_USER_AGENT == ANONYMOUS_USER_AGENT
    budget = ShopifyNormalizationHarnessBudget()
    for _index in range(5):
        budget.consume_search()
        budget.consume_get_product()
    with pytest.raises(ShopifyNormalizationHarnessError, match="search_catalog budget exceeded"):
        budget.consume_search()
    with pytest.raises(ShopifyNormalizationHarnessError, match="get_product budget exceeded"):
        budget.consume_get_product()


def test_owner_harness_prohibits_lookup_and_pagination() -> None:
    budget = ShopifyNormalizationHarnessBudget()
    with pytest.raises(ShopifyNormalizationHarnessError, match="lookup_catalog prohibited"):
        budget.reject_lookup()
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        budget.reject_pagination()
    assert budget.pagination_followed is True


def _replace_response_pagination(transport: MemoryTransport, pagination: dict) -> None:
    for envelope in transport.by_query.values():
        envelope["result"]["structuredContent"]["pagination"] = pagination


def _assert_first_page_budget(transport: MemoryTransport, summary) -> None:
    assert summary.pagination_followed is False
    assert summary.pagination_metadata_observed is True
    assert summary.search_call_count == 5
    assert summary.get_product_call_count == 5
    assert summary.lookup_count == 0
    assert summary.products_with_stable_source_product_id == 5
    assert summary.variants_with_stable_source_variant_id == 6
    names = [name for name, _arguments in transport.calls]
    assert names.count(SEARCH_TOOL) == 5
    assert names.count(GET_PRODUCT_TOOL) == 5
    assert len(transport.calls) == 10
    for _name, arguments in transport.calls:
        pagination = arguments["catalog"].get("pagination") or {}
        assert "cursor" not in pagination
        assert "page" not in pagination
        encoded = json.dumps(arguments)
        assert RETURNED_PAGE_CURSOR not in encoded
        assert '"page": 2' not in encoded
    assert RETURNED_PAGE_CURSOR not in json.dumps(summary.to_dict())


def test_response_cursor_does_not_fail_or_follow() -> None:
    transport = _diversified_transport()
    _replace_response_pagination(transport, {"cursor": RETURNED_PAGE_CURSOR})
    summary = _run(transport)
    _assert_first_page_budget(transport, summary)


def test_has_next_page_does_not_fail_or_follow() -> None:
    transport = _diversified_transport()
    _replace_response_pagination(transport, {"has_next_page": True})
    summary = _run(transport)
    _assert_first_page_budget(transport, summary)


def test_returned_page_metadata_is_not_copied_into_another_request() -> None:
    transport = _diversified_transport()
    _replace_response_pagination(
        transport,
        {"has_next_page": True, "cursor": RETURNED_PAGE_CURSOR, "page": 2},
    )
    summary = _run(transport)
    _assert_first_page_budget(transport, summary)
    assert summary.categories_normalized_successfully == tuple(
        category_id for category_id, _query in OWNER_NORMALIZATION_CATEGORIES
    )


def test_outgoing_pagination_cursor_and_page_fail_closed() -> None:
    profile = staging_normalization_profile()
    search = build_search_catalog_arguments("wireless earbuds", profile=profile)
    search["catalog"]["pagination"]["cursor"] = RETURNED_PAGE_CURSOR
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        _assert_request_in_bounds(SEARCH_TOOL, search)
    page_two = build_search_catalog_arguments("gaming laptop", profile=profile)
    page_two["catalog"]["pagination"]["page"] = 2
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        _assert_request_in_bounds(SEARCH_TOOL, page_two)
    detail = build_get_product_arguments("gid://shopify/p/norm-earbuds", profile=profile)
    detail["catalog"]["pagination"] = {"cursor": RETURNED_PAGE_CURSOR}
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        _assert_request_in_bounds(GET_PRODUCT_TOOL, detail)


def test_owner_harness_requires_exact_staging_profile_and_does_not_call() -> None:
    profile = staging_normalization_profile()
    assert profile.url == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
    assert_owner_harness_profile(profile.url)
    transport = MemoryTransport({}, {})
    with pytest.raises(ShopifyNormalizationHarnessError, match="exact deployed staging"):
        run_shopify_normalization_validation(
            transport,
            profile_url=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
            live=False,
        )
    with pytest.raises(ShopifyNormalizationHarnessError, match="exact deployed staging"):
        run_shopify_normalization_validation(
            transport,
            profile_url="https://example.com/ucp/agent-profiles/piqsavi.json",
            live=False,
        )
    assert transport.calls == []


def test_owner_harness_summary_preserves_identity_without_raw_payload(tmp_path: Path) -> None:
    transport = _diversified_transport()
    summary = run_shopify_normalization_validation(
        transport,
        profile_url=PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
        live=False,
        now=CHECKED,
    )
    assert summary.search_call_count == 5
    assert summary.get_product_call_count == 5
    assert summary.lookup_count == 0
    assert summary.pagination_followed is False
    assert summary.pagination_metadata_observed is True
    assert summary.raw_payload_persisted is False
    assert summary.raw_response_persistence is False
    assert summary.production_certification is False
    assert summary.sprint_38_started is False
    assert summary.sprint_32_closed is False
    assert summary.sprint_41_started is False
    assert summary.owner_live_validation is False
    assert summary.cursor_executed_live_harness is False
    assert "live_execution" not in summary.to_dict()
    assert summary.fabricated_shipping_count == 0
    assert summary.fabricated_voucher_count == 0
    assert summary.fabricated_tax_count == 0
    assert summary.market == "PH"
    assert summary.agent_profile_source == "piqsavi"
    assert summary.staging_profile_exact_url_classification == EXACT_DEPLOYED_STAGING_CLASSIFICATION
    assert summary.categories_attempted == tuple(
        category_id for category_id, _query in OWNER_NORMALIZATION_CATEGORIES
    )
    assert set(summary.categories_normalized_successfully) == {
        "wireless_earbuds",
        "gaming_laptop",
        "mechanical_keyboard",
        "usb_c_charger",
        "phone_case",
    }
    assert summary.currency_codes == ("EUR", "INR", "JPY", "PHP", "USD")
    assert summary.currencies_observed_count == 5
    assert summary.different_variant_conflicts_correctly_held_apart_count >= 1
    assert summary.ambiguous_or_insufficient_matches_count >= 1
    assert summary.products_with_stable_source_product_id == 5
    assert summary.variants_with_stable_source_variant_id == 6
    assert summary.search_variant_ids_observed_count == 6
    assert summary.detail_variant_ids_observed_count == 6
    assert summary.search_variants_confirmed_in_detail_count == 6
    assert summary.listing_prices_preserved_as_integer_minor_units == 12
    assert summary.listing_prices_preserved_as_integer_minor_units != (
        summary.products_with_stable_source_product_id
    )
    assert summary.availability_unknown_count == 0
    assert summary.availability_non_unknown_count == 12
    assert summary.availability_normalized_count == summary.availability_non_unknown_count
    names = [name for name, _arguments in transport.calls]
    assert names.count("search_catalog") == 5
    assert names.count("get_product") == 5
    assert FORBIDDEN_LOOKUP_TOOL not in names
    for _name, arguments in transport.calls:
        catalog = arguments["catalog"]
        pagination = catalog.get("pagination") or {}
        assert "cursor" not in pagination
        assert "page" not in pagination
        assert RETURNED_PAGE_CURSOR not in json.dumps(arguments)
        assert arguments["meta"]["ucp-agent"]["profile"] == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
    blob = json.dumps(summary.to_dict())
    assert RAW_SENTINEL not in blob
    assert RETURNED_PAGE_CURSOR not in blob
    assert "gid://shopify/p/norm-earbuds" not in blob
    assert stable_source_digest("gid://shopify/p/norm-earbuds") in summary.source_id_digests
    outside = tmp_path / "summary"
    path = write_normalization_summary(summary, outside, live=False)
    written = path.read_text(encoding="utf-8")
    assert RAW_SENTINEL not in written
    assert RETURNED_PAGE_CURSOR not in written
    assert "gid://shopify/" not in written
    with pytest.raises(Exception, match="repository"):
        write_normalization_summary(summary, ROOT / "not-committed-summary", live=False)


def _run(transport: MemoryTransport, *, live: bool = False):
    return run_shopify_normalization_validation(
        transport,
        profile_url=PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
        live=live,
        now=CHECKED,
    )


def _search_queries(transport: MemoryTransport) -> list[str]:
    return [
        arguments["catalog"]["query"]
        for name, arguments in transport.calls
        if name == "search_catalog"
    ]


def _empty_catalog() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"isError": False, "structuredContent": {"products": []}},
    }


def test_stable_product_count_uses_distinct_search_to_detail_identities() -> None:
    summary = _run(_diversified_transport())
    assert summary.products_with_stable_source_product_id == 5
    assert summary.listing_prices_preserved_as_integer_minor_units == 12
    assert summary.products_with_stable_source_product_id != (
        summary.listing_prices_preserved_as_integer_minor_units
    )


def test_changed_product_id_between_search_and_detail_fails_closed() -> None:
    transport = _diversified_transport()
    changed = _catalog_product(
        product_id="gid://shopify/p/changed-laptop",
        title="Gaming laptop",
        amount=20002,
        currency="USD",
    )
    transport.by_id["gid://shopify/p/norm-laptop"] = _envelope(changed)
    with pytest.raises(ShopifyNormalizationHarnessError, match="product ID disappears"):
        _run(transport)


def test_search_variant_confirmed_in_detail_counts_stable() -> None:
    summary = _run(_diversified_transport())
    assert summary.search_variant_ids_observed_count == 6
    assert summary.search_variants_confirmed_in_detail_count == 6
    assert summary.variants_with_stable_source_variant_id == 6
    assert summary.detail_variant_ids_observed_count == 6


def test_search_variant_missing_from_detail_fails_closed() -> None:
    transport = _diversified_transport()
    red_only = _catalog_product(
        product_id="gid://shopify/p/norm-keyboard",
        title="Mechanical keyboard",
        amount=8999,
        currency="EUR",
        variants=[
            _variant(
                variant_id="gid://shopify/ProductVariant/keyboard-red",
                amount=8999,
                currency="EUR",
            )
        ],
    )
    transport.by_id["gid://shopify/p/norm-keyboard"] = _envelope(
        red_only, pagination={"has_next_page": True}
    )
    with pytest.raises(
        ShopifyNormalizationHarnessError, match="search_variant_missing_from_get_product"
    ):
        _run(transport)


def test_additional_detail_only_variant_is_allowed() -> None:
    transport = _diversified_transport()
    detail = _catalog_product(
        product_id="gid://shopify/p/norm-keyboard",
        title="Mechanical keyboard",
        amount=8999,
        currency="EUR",
        variants=[
            _variant(
                variant_id="gid://shopify/ProductVariant/keyboard-red",
                amount=8999,
                currency="EUR",
            ),
            _variant(
                variant_id="gid://shopify/ProductVariant/keyboard-blue",
                amount=8999,
                currency="EUR",
            ),
            _variant(
                variant_id="gid://shopify/ProductVariant/keyboard-green",
                amount=8999,
                currency="EUR",
            ),
        ],
    )
    transport.by_id["gid://shopify/p/norm-keyboard"] = _envelope(
        detail, pagination={"has_next_page": True}
    )
    summary = _run(transport)
    assert summary.search_variant_ids_observed_count == 6
    assert summary.detail_variant_ids_observed_count == 7
    assert summary.search_variants_confirmed_in_detail_count == 6
    assert summary.variants_with_stable_source_variant_id == 6
    assert summary.products_with_stable_source_product_id == 5


def test_duplicate_offer_rows_do_not_inflate_stable_counts() -> None:
    transport = _diversified_transport()
    duplicate_id = "gid://shopify/ProductVariant/earbuds-dup"
    product = _catalog_product(
        product_id="gid://shopify/p/norm-earbuds",
        title="Wireless earbuds",
        amount=10001,
        currency="PHP",
        variants=[
            _variant(variant_id=duplicate_id, amount=10001, currency="PHP"),
            _variant(variant_id=duplicate_id, amount=10001, currency="PHP"),
        ],
    )
    envelope = _envelope(product, pagination={"has_next_page": True})
    transport.by_query["wireless earbuds"] = envelope
    transport.by_id["gid://shopify/p/norm-earbuds"] = envelope
    summary = _run(transport)
    assert summary.products_with_stable_source_product_id == 5
    assert summary.variants_with_stable_source_variant_id == 6
    assert summary.search_variant_ids_observed_count == 6
    assert summary.search_variants_confirmed_in_detail_count == 6
    assert summary.listing_prices_preserved_as_integer_minor_units == 14


def test_five_of_five_category_success_passes() -> None:
    transport = _diversified_transport()
    summary = _run(transport)
    expected = tuple(category_id for category_id, _query in OWNER_NORMALIZATION_CATEGORIES)
    assert summary.categories_attempted == expected
    assert summary.categories_normalized_successfully == expected
    assert summary.search_call_count == 5
    assert summary.get_product_call_count == 5
    assert _search_queries(transport) == [
        query for _category_id, query in OWNER_NORMALIZATION_CATEGORIES
    ]


def test_four_of_five_category_success_fails_closed() -> None:
    transport = _diversified_transport()
    transport.by_query["gaming laptop"] = _empty_catalog()
    with pytest.raises(
        ShopifyNormalizationHarnessError,
        match="category_normalization_incomplete:gaming_laptop",
    ):
        _run(transport)
    assert _search_queries(transport) == [
        query for _category_id, query in OWNER_NORMALIZATION_CATEGORIES
    ]
    assert len(transport.calls) == 9
    assert sum(name == "get_product" for name, _arguments in transport.calls) == 4
    assert sum(name == "search_catalog" for name, _arguments in transport.calls) == 5


def test_zero_of_five_category_success_fails_closed() -> None:
    transport = _diversified_transport()
    for query in list(transport.by_query):
        transport.by_query[query] = _empty_catalog()
    with pytest.raises(
        ShopifyNormalizationHarnessError,
        match="category_normalization_incomplete:wireless_earbuds",
    ):
        _run(transport)
    assert _search_queries(transport) == [
        query for _category_id, query in OWNER_NORMALIZATION_CATEGORIES
    ]
    assert sum(name == "search_catalog" for name, _arguments in transport.calls) == 5
    assert sum(name == "get_product" for name, _arguments in transport.calls) == 0


def test_incomplete_category_does_not_attempt_a_fallback_search() -> None:
    transport = _diversified_transport()
    transport.by_query["phone case"] = _empty_catalog()
    with pytest.raises(
        ShopifyNormalizationHarnessError,
        match="category_normalization_incomplete:phone_case",
    ):
        _run(transport)
    queries = _search_queries(transport)
    assert queries == [query for _category_id, query in OWNER_NORMALIZATION_CATEGORIES]
    assert len(queries) == 5
    assert "fallback gadget" not in queries


def test_unknown_availability_is_not_positive_evidence() -> None:
    transport = _diversified_transport()
    product = transport.by_query["wireless earbuds"]["result"]["structuredContent"]["products"][0]
    for variant in product["variants"]:
        variant.pop("availability")
    summary = _run(transport)
    assert summary.availability_unknown_count == 2
    assert summary.availability_non_unknown_count == 10
    assert summary.availability_normalized_count == 10
    assert summary.availability_normalized_count == summary.availability_non_unknown_count
    assert summary.availability_normalized_count != (
        summary.availability_non_unknown_count + summary.availability_unknown_count
    )


def test_known_availability_is_counted_separately_from_unknown() -> None:
    transport = _diversified_transport()
    earbuds = transport.by_query["wireless earbuds"]["result"]["structuredContent"]["products"][0]
    for variant in earbuds["variants"]:
        variant.pop("availability")
    laptop = transport.by_query["gaming laptop"]["result"]["structuredContent"]["products"][0]
    for variant in laptop["variants"]:
        variant["availability"] = {"available": False}
    summary = _run(transport)
    assert summary.availability_unknown_count == 2
    assert summary.availability_non_unknown_count == 10
    assert summary.availability_normalized_count == summary.availability_non_unknown_count


def test_live_execution_field_is_removed() -> None:
    summary = _run(_diversified_transport())
    assert not hasattr(summary, "live_execution")
    assert "live_execution" not in summary.to_dict()


def test_owner_live_validation_is_true_only_for_owner_live_mode() -> None:
    synthetic = _run(_diversified_transport(), live=False)
    owner_live = _run(_diversified_transport(), live=True)
    assert synthetic.owner_live_validation is False
    assert owner_live.owner_live_validation is True
    assert owner_live.sprint_38_started is False
    assert owner_live.sprint_32_closed is False
    assert owner_live.sprint_41_started is False
    assert owner_live.production_certification is False
    assert owner_live.cursor_executed_live_harness is False
    assert "live_execution" not in owner_live.to_dict()


def test_persisted_summary_has_no_raw_shopify_ids_or_payload(tmp_path: Path) -> None:
    summary = _run(_diversified_transport())
    path = write_normalization_summary(summary, tmp_path / "out", live=False)
    written = path.read_text(encoding="utf-8")
    payload = json.loads(written)
    assert "gid://shopify/" not in written
    assert RETURNED_PAGE_CURSOR not in written
    assert payload["pagination_followed"] is False
    assert payload["pagination_metadata_observed"] is True
    assert RAW_SENTINEL not in written
    assert '"raw_payload"' not in written
    assert '"description"' not in written
    assert '"media"' not in written
    assert '"metadata"' not in written
    assert "live_execution" not in payload
    assert payload["production_certification"] is False
    assert payload["owner_live_validation"] is False
    for digest in payload["source_id_digests"]:
        assert len(digest) == 64
        int(digest, 16)
    assert stable_source_digest("gid://shopify/p/norm-earbuds") in payload["source_id_digests"]
    assert (
        stable_source_digest("gid://shopify/ProductVariant/keyboard-red")
        in (payload["source_id_digests"])
    )


def test_owner_harness_fails_closed_on_transport_errors() -> None:
    jsonrpc = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32001, "message": "UCP discovery failed"},
    }
    transport = MemoryTransport({}, {}, search_override=jsonrpc)
    with pytest.raises(ShopifyNormalizationHarnessError, match="jsonrpc_error"):
        run_shopify_normalization_validation(
            transport,
            profile_url=PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
            live=False,
            now=CHECKED,
        )
    is_error = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"isError": True, "structuredContent": {"messages": []}},
    }
    transport = MemoryTransport({}, {}, search_override=is_error)
    with pytest.raises(ShopifyNormalizationHarnessError, match="mcp_is_error"):
        run_shopify_normalization_validation(
            transport,
            profile_url=PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
            live=False,
            now=CHECKED,
        )

    def _wrong_id(_arguments: dict) -> dict:
        product = _catalog_product(
            product_id="gid://shopify/p/other",
            title="Wireless earbuds",
            amount=10001,
            currency="PHP",
        )
        return _envelope(product)

    transport = _diversified_transport()
    transport.detail_override = _wrong_id
    with pytest.raises(ShopifyNormalizationHarnessError, match="product ID disappears"):
        run_shopify_normalization_validation(
            transport,
            profile_url=PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
            live=False,
            now=CHECKED,
        )


def test_owner_script_without_live_does_not_call_shopify(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args, **_kwargs):
        raise AssertionError("Shopify must not be called")

    monkeypatch.setattr("httpx.post", _boom)
    assert OWNER_LIVE_HARNESS_RUN_BY_CURSOR is False
    assert harness_main([]) == 2


def test_library_modules_do_not_import_http_clients() -> None:
    paths = (
        ROOT / "app/marketplace/normalization/shopify_global_catalog.py",
        ROOT / "app/research/shopify_global_catalog_reliability.py",
        ROOT / "app/research/shopify_global_catalog_normalization_harness.py",
    )
    forbidden = {"httpx", "requests", "urllib", "socket"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert imported.isdisjoint(forbidden)
    script = (ROOT / "scripts/shopify_global_catalog_normalization_validation.py").read_text(
        encoding="utf-8"
    )
    assert "httpx.post(" in script
    assert "https://catalog.shopify.com/api/ucp/mcp" in script
    assert "--live" in script


def test_production_catalogs_remain_unchanged() -> None:
    assert len(production_research_provider_registry().list_providers()) == 1
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    assert len(production_research_provider_certification_evidence_catalog().list_records()) == 4
    assert len(production_research_provider_routing_policy_catalog().list_records()) == 0
    assert_production_shopify_evidence_only()
    evidence = production_research_provider_certification_evidence_catalog().list_records()[0]
    service = ResearchProviderCertificationDecisionService(
        production_research_provider_certification_evidence_catalog(),
        production_research_provider_certification_catalog(),
        production_research_provider_registry(),
    )
    result = service.decide(
        CertificationDecisionRequest(
            provider_id=evidence.provider_id,
            capability=evidence.capability,
            market=evidence.market,
            source=evidence.source,
            requested_status="certified",
            requested_policy="allowed",
            certification_version=evidence.certification_version or "not-registered",
            reviewer="Sprint 32 normalization test",
            decided_at=date(2026, 9, 23),
        )
    )
    assert result.accepted is True
    assert result.reason == "approved"
    assert result.certification is not None
    assert len(production_research_provider_registry().list_providers()) == 1
    assert len(production_research_provider_certification_catalog().list_records()) == 4


def test_affiliate_status_does_not_change_normalized_price() -> None:
    offer = _offer(amount=4242, currency="EUR")
    assert offer.economics.dominant_amount_minor == 4242
    assert offer.economics.voucher is not None
    assert offer.economics.voucher.applied is False
    candidate = shopify_normalization_reliability_candidate()
    assert candidate.descriptor.affiliate_commission_rate is None
    assert "affiliate" not in " ".join(shopify_candidate_eligibility(candidate.descriptor))
    AffiliateNeutralitySnapshot()
    with pytest.raises(ValueError, match="affiliate influence"):
        AffiliateNeutralitySnapshot(commission_influenced_ordering=True)


def test_freshness_policy_and_sprint_status_remain_honest() -> None:
    index = shopify_capability_policy_index()
    assert index["freshness_timestamp"].shopper_applicability == "unknown"
    assert index["normalization_within_piqsavi"].technical_exposure == "unknown"
    assert index["normalization_within_piqsavi"].policy == "restricted"
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    sprint41 = SPRINT41.read_text(encoding="utf-8")
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "Sprint 41 remains unstarted" in sprint32
    assert "LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED" in sprint32
    blockers = sprint32.split("### Closure blockers (current)", 1)[1].split(
        "### Production defaults", 1
    )[0]
    assert "Owner live normalization validation is still required" not in blockers
    assert "Engineering kill-switch validation PASSED" in blockers
    assert "DEPLOYED OPERATIONAL KILL-SWITCH DRILL remains Sprint 38/41" in blockers
    status = next(line for line in sprint32.splitlines() if line.startswith("**Status:**"))
    assert "COMPLETE / CLOSED" in status
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    sprint41_status = sprint41.split("**Status:**", 1)[1].splitlines()[0].strip()
    assert sprint41_status.startswith("Planned")
    assert "not started" in sprint41_status.casefold()
    blockers = sprint32.split("### Closure blockers (current)", 1)[1].split(
        "### Production defaults", 1
    )[0]
    assert "must be rerun" not in blockers
    assert "five distinct categories" in blockers


def test_availability_is_normalized_from_shopify_status() -> None:
    offer = _offer()
    assert offer.source.availability == ProductAvailability.IN_STOCK
    product, variant = _product()
    variant["availability"] = {"available": False}
    unavailable = normalize_shopify_global_catalog_offer(product, variant, checked_at=CHECKED)
    assert unavailable.source.availability == ProductAvailability.OUT_OF_STOCK
