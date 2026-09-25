"""Owner-run Shopify normalization validation harness.

Library only. It does not perform HTTP. The owner CLI may later call the
documented Global Catalog endpoint with the exact deployed staging profile.
Cursor must not execute that live path.

Payloads stay in memory. The summary stores counts and non-reversible
digests, not raw Shopify product responses.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.entities.marketplace_data import ProductAvailability
from app.marketplace.normalization.shopify_global_catalog import (
    ObservationKind,
    ShopifyIdentityComparison,
    ShopifyNormalizedOffer,
    compare_shopify_variant_identity,
    integer_source_minor_amount,
    normalize_shopify_global_catalog_offer,
    shopify_listing_price,
)
from app.research.shopify_global_catalog_ph_probe import (
    AGENT_PROFILE_SOURCE_PIQSAVI,
    AGENT_PROFILE_USAGE_PIQSAVI,
    ANONYMOUS_USER_AGENT,
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    PH_COUNTRY,
    SEARCH_TOOL,
    AgentProfileSelection,
    CatalogTransport,
    LiveProbeOutputInsideRepositoryError,
    ProbeResponseError,
    assert_live_probe_output_outside_repository,
    build_get_product_arguments,
    build_search_catalog_arguments,
    products_from_catalog_payload,
    validate_catalog_tool_response,
    variants_from_product,
)
from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    piqsavi_profile_deployed_for_url,
)

MAX_SEARCH_CATALOG_CALLS = 5
MAX_GET_PRODUCT_CALLS = 5
LOOKUP_CATALOG_CALLS = 0
OWNER_HARNESS_USER_AGENT = ANONYMOUS_USER_AGENT
OWNER_LIVE_HARNESS_RUN_BY_CURSOR = False
EXACT_DEPLOYED_STAGING_CLASSIFICATION = "exact_deployed_staging"
OWNER_NORMALIZATION_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("wireless_earbuds", "wireless earbuds"),
    ("gaming_laptop", "gaming laptop"),
    ("mechanical_keyboard", "mechanical keyboard"),
    ("usb_c_charger", "USB-C charger"),
    ("phone_case", "phone case"),
)
_RAW_SUMMARY_MARKERS = (
    '"description"',
    '"media"',
    '"metadata"',
    '"html"',
    '"checkout_url"',
    '"raw_payload"',
)


class ShopifyNormalizationHarnessError(RuntimeError):
    """The owner validation failed closed."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass
class ShopifyNormalizationHarnessBudget:
    """Hard caps for the owner harness. Lookup and pagination are prohibited."""

    search_calls: int = 0
    get_product_calls: int = 0
    lookup_calls: int = 0
    pagination_followed: bool = False

    def consume_search(self) -> None:
        if self.search_calls >= MAX_SEARCH_CATALOG_CALLS:
            raise ShopifyNormalizationHarnessError("search_catalog budget exceeded")
        self.search_calls += 1

    def consume_get_product(self) -> None:
        if self.get_product_calls >= MAX_GET_PRODUCT_CALLS:
            raise ShopifyNormalizationHarnessError("get_product budget exceeded")
        self.get_product_calls += 1

    def reject_lookup(self) -> None:
        self.lookup_calls += 1
        raise ShopifyNormalizationHarnessError("lookup_catalog prohibited")

    def reject_pagination(self) -> None:
        """Fail closed only when PiqSavi follows another page.

        A cursor or ``has_next_page`` returned on the first page is ignored
        metadata and must not call this method.
        """

        self.pagination_followed = True
        raise ShopifyNormalizationHarnessError("pagination prohibited")


@dataclass(frozen=True, slots=True)
class ShopifyNormalizationValidationSummary:
    """Minimized owner-run summary. Not a raw catalog artifact."""

    generated_at: str
    agent_profile_source: str
    staging_profile_exact_url_classification: str
    market: str
    search_call_count: int
    get_product_call_count: int
    lookup_count: int
    pagination_followed: bool
    pagination_metadata_observed: bool
    raw_payload_persisted: bool
    categories_attempted: tuple[str, ...]
    categories_normalized_successfully: tuple[str, ...]
    products_with_stable_source_product_id: int
    variants_with_stable_source_variant_id: int
    search_variant_ids_observed_count: int
    detail_variant_ids_observed_count: int
    search_variants_confirmed_in_detail_count: int
    listing_prices_preserved_as_integer_minor_units: int
    currencies_observed_count: int
    currency_codes: tuple[str, ...]
    seller_identity_present_count: int
    availability_normalized_count: int
    availability_non_unknown_count: int
    availability_unknown_count: int
    canonical_parsing_attempted_count: int
    exact_variant_comparisons_count: int
    different_variant_conflicts_correctly_held_apart_count: int
    ambiguous_or_insufficient_matches_count: int
    fabricated_shipping_count: int
    fabricated_voucher_count: int
    fabricated_tax_count: int
    raw_response_persistence: bool
    production_certification: bool
    sprint_38_started: bool
    source_id_digests: tuple[str, ...]
    owner_live_validation: bool
    sprint_32_closed: bool
    sprint_41_started: bool
    cursor_executed_live_harness: bool

    def __post_init__(self) -> None:
        if (
            self.production_certification
            or self.sprint_38_started
            or self.sprint_32_closed
            or self.sprint_41_started
            or self.cursor_executed_live_harness
            or self.raw_payload_persisted
            or self.raw_response_persistence
            or self.pagination_followed
            or self.lookup_count != 0
        ):
            raise ShopifyNormalizationHarnessError(
                "validation summary is not certification evidence"
            )
        if (
            len(self.categories_attempted) != MAX_SEARCH_CATALOG_CALLS
            or len(self.categories_normalized_successfully) != MAX_SEARCH_CATALOG_CALLS
            or self.search_call_count != MAX_SEARCH_CATALOG_CALLS
            or self.get_product_call_count != MAX_GET_PRODUCT_CALLS
        ):
            raise ShopifyNormalizationHarnessError("category_normalization_incomplete")
        if self.availability_normalized_count != self.availability_non_unknown_count:
            raise ShopifyNormalizationHarnessError("availability count includes unknown")
        if (
            self.variants_with_stable_source_variant_id
            != self.search_variants_confirmed_in_detail_count
        ):
            raise ShopifyNormalizationHarnessError(
                "variant stability count is not confirmed continuity"
            )
        if self.products_with_stable_source_product_id > len(
            self.categories_normalized_successfully
        ):
            raise ShopifyNormalizationHarnessError("stable product count exceeds selected products")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "generated_at": self.generated_at,
            "agent_profile_source": self.agent_profile_source,
            "staging_profile_exact_url_classification": (
                self.staging_profile_exact_url_classification
            ),
            "market": self.market,
            "search_call_count": self.search_call_count,
            "get_product_call_count": self.get_product_call_count,
            "lookup_count": self.lookup_count,
            "pagination_followed": self.pagination_followed,
            "pagination_metadata_observed": self.pagination_metadata_observed,
            "raw_payload_persisted": self.raw_payload_persisted,
            "categories_attempted": list(self.categories_attempted),
            "categories_normalized_successfully": list(self.categories_normalized_successfully),
            "products_with_stable_source_product_id": (self.products_with_stable_source_product_id),
            "variants_with_stable_source_variant_id": self.variants_with_stable_source_variant_id,
            "search_variant_ids_observed_count": self.search_variant_ids_observed_count,
            "detail_variant_ids_observed_count": self.detail_variant_ids_observed_count,
            "search_variants_confirmed_in_detail_count": (
                self.search_variants_confirmed_in_detail_count
            ),
            "listing_prices_preserved_as_integer_minor_units": (
                self.listing_prices_preserved_as_integer_minor_units
            ),
            "currencies_observed_count": self.currencies_observed_count,
            "currency_codes": list(self.currency_codes),
            "seller_identity_present_count": self.seller_identity_present_count,
            "availability_normalized_count": self.availability_normalized_count,
            "availability_non_unknown_count": self.availability_non_unknown_count,
            "availability_unknown_count": self.availability_unknown_count,
            "canonical_parsing_attempted_count": self.canonical_parsing_attempted_count,
            "exact_variant_comparisons_count": self.exact_variant_comparisons_count,
            "different_variant_conflicts_correctly_held_apart_count": (
                self.different_variant_conflicts_correctly_held_apart_count
            ),
            "ambiguous_or_insufficient_matches_count": (
                self.ambiguous_or_insufficient_matches_count
            ),
            "fabricated_shipping_count": self.fabricated_shipping_count,
            "fabricated_voucher_count": self.fabricated_voucher_count,
            "fabricated_tax_count": self.fabricated_tax_count,
            "raw_response_persistence": self.raw_response_persistence,
            "production_certification": self.production_certification,
            "sprint_38_started": self.sprint_38_started,
            "source_id_digests": list(self.source_id_digests),
            "owner_live_validation": self.owner_live_validation,
            "sprint_32_closed": self.sprint_32_closed,
            "sprint_41_started": self.sprint_41_started,
            "cursor_executed_live_harness": self.cursor_executed_live_harness,
        }
        assert_summary_has_no_raw_payload(payload)
        return payload


def staging_normalization_profile() -> AgentProfileSelection:
    """Exact deployed staging profile. Production and arbitrary URLs are refused."""

    url = PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
    assert_owner_harness_profile(url)
    return AgentProfileSelection(
        source=AGENT_PROFILE_SOURCE_PIQSAVI,
        url=url,
        usage=AGENT_PROFILE_USAGE_PIQSAVI,
        not_piqsavi_identity=False,
        piqsavi_profile_deployed=piqsavi_profile_deployed_for_url(url),
        piqsavi_profile_staging_deployed=PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
        piqsavi_profile_production_deployed=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
        shopify_has_fetched_profile=SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    )


def assert_owner_harness_profile(url: str) -> None:
    """Fail unless the URL is the exact deployed staging PiqSavi profile."""

    if url != PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL:
        raise ShopifyNormalizationHarnessError(
            "selected profile is not the exact deployed staging profile"
        )
    if url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL:
        raise ShopifyNormalizationHarnessError("production profile is not unlocked")
    if not piqsavi_profile_deployed_for_url(url):
        raise ShopifyNormalizationHarnessError("staging profile is not deployed")


def stable_source_digest(value: str) -> str:
    """Non-reversible correlation digest. Not a raw Shopify id."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def assert_summary_has_no_raw_payload(payload: Mapping[str, Any]) -> None:
    blob = json.dumps(payload, sort_keys=True)
    if any(marker in blob for marker in _RAW_SUMMARY_MARKERS):
        raise ShopifyNormalizationHarnessError("raw payload written into summary")
    if "gid://shopify/" in blob:
        raise ShopifyNormalizationHarnessError("raw shopify id written into summary")


def assert_normalization_preserved_price(
    offer: ShopifyNormalizedOffer,
    *,
    amount_minor: int,
    currency: str,
) -> None:
    if offer.source.price_amount_minor != amount_minor:
        raise ShopifyNormalizationHarnessError("price minor amount changed during normalization")
    if offer.economics.listing.amount_minor != amount_minor:
        raise ShopifyNormalizationHarnessError("price minor amount changed during normalization")
    if offer.source.currency != currency or offer.economics.currency != currency:
        raise ShopifyNormalizationHarnessError("currency changed during normalization")
    if not isinstance(offer.economics.listing.amount_minor, int) or isinstance(
        offer.economics.listing.amount_minor, bool
    ):
        raise ShopifyNormalizationHarnessError("price minor amount changed during normalization")


def assert_no_fabricated_components(offer: ShopifyNormalizedOffer) -> None:
    shipping = offer.economics.shipping
    taxes = offer.economics.taxes
    voucher = offer.economics.voucher
    if shipping.amount_minor is not None or shipping.status != "unknown":
        raise ShopifyNormalizationHarnessError("unknown shipping became an amount")
    if shipping.amount_minor == 0:
        raise ShopifyNormalizationHarnessError("unknown shipping became zero")
    if taxes.amount_minor is not None or taxes.status != "unknown":
        raise ShopifyNormalizationHarnessError("unknown tax became an amount")
    if taxes.amount_minor == 0:
        raise ShopifyNormalizationHarnessError("unknown tax became zero")
    if voucher is None or voucher.applied or voucher.amount_minor is not None:
        raise ShopifyNormalizationHarnessError("unknown voucher became applied")
    if offer.economics.price_state == "final_effective_cost":
        raise ShopifyNormalizationHarnessError("effective price claimed final")
    if offer.economics.dominant_amount_minor != offer.source.price_amount_minor:
        raise ShopifyNormalizationHarnessError("unknown component reduced the listing price")


def assert_variants_not_silently_merged(decision: ShopifyIdentityComparison) -> None:
    if decision.source_variant_ids_conflict and decision.merged:
        raise ShopifyNormalizationHarnessError(
            "known source variant silently merged into another variant"
        )


def run_shopify_normalization_validation(
    transport: CatalogTransport,
    *,
    profile_url: str,
    live: bool,
    now: datetime | None = None,
) -> ShopifyNormalizationValidationSummary:
    """Validate in-memory catalog responses through the normalization adapter.

    ``live=True`` only labels an owner-supplied transport. This function does
    not open a socket. Cursor must leave ``OWNER_LIVE_HARNESS_RUN_BY_CURSOR``
    false and must not invoke the owner CLI.
    """

    if OWNER_LIVE_HARNESS_RUN_BY_CURSOR:
        raise ShopifyNormalizationHarnessError("cursor must not execute the owner harness")
    assert_owner_harness_profile(profile_url)
    profile = staging_normalization_profile()
    if profile.url != profile_url:
        raise ShopifyNormalizationHarnessError(
            "selected profile is not the exact deployed staging profile"
        )
    budget = ShopifyNormalizationHarnessBudget()
    checked_at = now or datetime.now(UTC)
    if checked_at.utcoffset() is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    observation: ObservationKind = "live" if live else "synthetic"
    offers: list[ShopifyNormalizedOffer] = []
    comparisons = 0
    held_apart = 0
    ambiguous = 0
    digests: set[str] = set()
    pagination_metadata_observed = False
    selected: list[tuple[str, str, list[ShopifyNormalizedOffer], frozenset[str]]] = []
    search_variant_ids: set[str] = set()
    detail_variant_ids: set[str] = set()
    confirmed_variant_ids: set[str] = set()
    stable_product_ids: set[str] = set()
    validated_categories: list[str] = []

    for category_id, query in OWNER_NORMALIZATION_CATEGORIES:
        budget.consume_search()
        arguments = build_search_catalog_arguments(query, profile=profile)
        _assert_request_in_bounds(SEARCH_TOOL, arguments)
        payload = transport.call_tool(SEARCH_TOOL, arguments)
        content = _accepted_content(payload)
        if _response_pagination_metadata_observed(content):
            pagination_metadata_observed = True
        products = products_from_catalog_payload(payload)
        product = next((item for item in products if _text(item.get("id"))), None)
        if product is None:
            continue
        product_id = str(product.get("id"))
        category_offers = _normalize_product(
            product, checked_at=checked_at, observation_kind=observation
        )
        if not category_offers:
            continue
        observed_search = _variant_id_set(product)
        search_variant_ids.update(observed_search)
        comparisons, held_apart, ambiguous = _tally(
            category_offers, comparisons, held_apart, ambiguous
        )
        offers.extend(category_offers)
        selected.append((category_id, product_id, category_offers, observed_search))
        digests.add(stable_source_digest(product_id))
        for variant_id in observed_search:
            digests.add(stable_source_digest(variant_id))

    for category_id, product_id, search_offers, observed_search in selected:
        budget.consume_get_product()
        arguments = build_get_product_arguments(product_id, profile=profile)
        _assert_request_in_bounds(GET_PRODUCT_TOOL, arguments)
        payload = transport.call_tool(GET_PRODUCT_TOOL, arguments)
        content = _accepted_content(payload)
        if _response_pagination_metadata_observed(content):
            pagination_metadata_observed = True
        products = products_from_catalog_payload(payload)
        detail = next((item for item in products if _text(item.get("id"))), None)
        if detail is None or str(detail.get("id")) != product_id:
            raise ShopifyNormalizationHarnessError(
                "product ID disappears between search and get_product"
            )
        observed_detail = _variant_id_set(detail)
        detail_variant_ids.update(observed_detail)
        if observed_search - observed_detail:
            raise ShopifyNormalizationHarnessError("search_variant_missing_from_get_product")
        confirmed_variant_ids.update(observed_search & observed_detail)
        stable_product_ids.add(product_id)
        detail_offers = _normalize_product(
            detail, checked_at=checked_at, observation_kind=observation
        )
        if not detail_offers:
            continue
        comparisons, held_apart, ambiguous = _tally(
            detail_offers, comparisons, held_apart, ambiguous
        )
        comparisons, held_apart, ambiguous = _compare_groups(
            search_offers,
            detail_offers,
            comparisons,
            held_apart,
            ambiguous,
        )
        offers.extend(detail_offers)
        for variant_id in observed_detail:
            digests.add(stable_source_digest(variant_id))
        validated_categories.append(category_id)

    for category_id, _query in OWNER_NORMALIZATION_CATEGORIES:
        if category_id not in validated_categories:
            raise ShopifyNormalizationHarnessError(
                f"category_normalization_incomplete:{category_id}"
            )
    if budget.search_calls != MAX_SEARCH_CATALOG_CALLS:
        raise ShopifyNormalizationHarnessError("category_normalization_incomplete")
    if budget.get_product_calls != MAX_GET_PRODUCT_CALLS:
        raise ShopifyNormalizationHarnessError("category_normalization_incomplete")
    if budget.lookup_calls != LOOKUP_CATALOG_CALLS or budget.pagination_followed:
        raise ShopifyNormalizationHarnessError("lookup or pagination occurred")
    currencies = tuple(sorted({offer.source.currency for offer in offers}))
    non_unknown, unknown = _availability_counts(offers)
    summary = ShopifyNormalizationValidationSummary(
        generated_at=checked_at.isoformat(),
        agent_profile_source=AGENT_PROFILE_SOURCE_PIQSAVI,
        staging_profile_exact_url_classification=EXACT_DEPLOYED_STAGING_CLASSIFICATION,
        market=PH_COUNTRY,
        search_call_count=budget.search_calls,
        get_product_call_count=budget.get_product_calls,
        lookup_count=LOOKUP_CATALOG_CALLS,
        pagination_followed=False,
        pagination_metadata_observed=pagination_metadata_observed,
        raw_payload_persisted=False,
        categories_attempted=tuple(
            category_id for category_id, _query in OWNER_NORMALIZATION_CATEGORIES
        ),
        categories_normalized_successfully=tuple(validated_categories),
        products_with_stable_source_product_id=len(stable_product_ids),
        variants_with_stable_source_variant_id=len(confirmed_variant_ids),
        search_variant_ids_observed_count=len(search_variant_ids),
        detail_variant_ids_observed_count=len(detail_variant_ids),
        search_variants_confirmed_in_detail_count=len(confirmed_variant_ids),
        listing_prices_preserved_as_integer_minor_units=sum(
            1
            for offer in offers
            if offer.economics.listing.amount_minor == offer.source.price_amount_minor
        ),
        currencies_observed_count=len(currencies),
        currency_codes=currencies,
        seller_identity_present_count=sum(1 for offer in offers if offer.source.seller_identity),
        availability_normalized_count=non_unknown,
        availability_non_unknown_count=non_unknown,
        availability_unknown_count=unknown,
        canonical_parsing_attempted_count=len(offers),
        exact_variant_comparisons_count=comparisons,
        different_variant_conflicts_correctly_held_apart_count=held_apart,
        ambiguous_or_insufficient_matches_count=ambiguous,
        fabricated_shipping_count=0,
        fabricated_voucher_count=0,
        fabricated_tax_count=0,
        raw_response_persistence=False,
        production_certification=False,
        sprint_38_started=False,
        source_id_digests=tuple(sorted(digests)),
        owner_live_validation=live,
        sprint_32_closed=False,
        sprint_41_started=False,
        cursor_executed_live_harness=False,
    )
    assert_summary_has_no_raw_payload(summary.to_dict())
    return summary


def write_normalization_summary(
    summary: ShopifyNormalizationValidationSummary,
    output_dir: Path,
    *,
    live: bool,
    pacing: Mapping[str, Any] | None = None,
) -> Path:
    """Write the minimized summary only. Live output must stay outside Git."""

    if live:
        assert_live_probe_output_outside_repository(output_dir)
    elif _path_inside_repository(output_dir):
        raise LiveProbeOutputInsideRepositoryError(
            "normalization summary must not be written inside the repository"
        )
    payload = summary.to_dict()
    if pacing:
        payload.update(dict(pacing))
    assert_summary_has_no_raw_payload(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "shopify-normalization-validation-summary.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _normalize_product(
    product: dict[str, Any],
    *,
    checked_at: datetime,
    observation_kind: ObservationKind,
) -> list[ShopifyNormalizedOffer]:
    offers: list[ShopifyNormalizedOffer] = []
    for variant in variants_from_product(product):
        if not isinstance(variant, dict):
            continue
        price = shopify_listing_price(product, variant)
        amount = integer_source_minor_amount(price)
        currency = ""
        if isinstance(price, Mapping):
            raw_currency = price.get("currency")
            if raw_currency is not None:
                currency = str(raw_currency).strip().upper()
        offer = normalize_shopify_global_catalog_offer(
            product,
            variant,
            checked_at=checked_at,
            observation_kind=observation_kind,
            ph_query_context=True,
        )
        if amount is None or not currency:
            raise ShopifyNormalizationHarnessError("missing price or currency before normalization")
        assert_normalization_preserved_price(offer, amount_minor=amount, currency=currency)
        assert_no_fabricated_components(offer)
        if offer.raw_response_persisted:
            raise ShopifyNormalizationHarnessError("raw payload persisted")
        offers.append(offer)
    return offers


def _compare_groups(
    left_offers: list[ShopifyNormalizedOffer],
    right_offers: list[ShopifyNormalizedOffer],
    comparisons: int,
    held_apart: int,
    ambiguous: int,
) -> tuple[int, int, int]:
    for left in left_offers:
        for right in right_offers:
            decision = compare_shopify_variant_identity(left, right)
            assert_variants_not_silently_merged(decision)
            comparisons += 1
            if decision.source_variant_ids_conflict and not decision.merged:
                held_apart += 1
            if decision.relation in {"insufficient_information", "ambiguous"}:
                ambiguous += 1
    return comparisons, held_apart, ambiguous


def _tally(
    offers: list[ShopifyNormalizedOffer],
    comparisons: int,
    held_apart: int,
    ambiguous: int,
) -> tuple[int, int, int]:
    if len(offers) < 2:
        return comparisons, held_apart, ambiguous
    for index in range(len(offers) - 1):
        decision = compare_shopify_variant_identity(offers[index], offers[index + 1])
        assert_variants_not_silently_merged(decision)
        comparisons += 1
        if decision.source_variant_ids_conflict and not decision.merged:
            held_apart += 1
        if decision.relation in {"insufficient_information", "ambiguous"}:
            ambiguous += 1
    return comparisons, held_apart, ambiguous


def _accepted_content(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_catalog_tool_response(payload)
    except ProbeResponseError as exc:
        message = str(exc).casefold()
        if payload.get("error") is not None:
            raise ShopifyNormalizationHarnessError("jsonrpc_error") from None
        result = payload.get("result")
        if isinstance(result, dict) and result.get("isError") is True:
            raise ShopifyNormalizationHarnessError("mcp_is_error") from None
        if "json-rpc" in message or "jsonrpc" in message:
            raise ShopifyNormalizationHarnessError("jsonrpc_error") from None
        raise ShopifyNormalizationHarnessError("malformed_catalog_response") from None


def _assert_request_in_bounds(tool_name: str, arguments: dict[str, Any]) -> None:
    if tool_name == FORBIDDEN_LOOKUP_TOOL:
        raise ShopifyNormalizationHarnessError("lookup_catalog prohibited")
    if tool_name not in {SEARCH_TOOL, GET_PRODUCT_TOOL}:
        raise ShopifyNormalizationHarnessError("unsupported catalog tool")
    catalog = arguments.get("catalog")
    if not isinstance(catalog, dict):
        raise ShopifyNormalizationHarnessError("malformed catalog arguments")
    pagination = catalog.get("pagination")
    if isinstance(pagination, dict) and (pagination.get("cursor") or pagination.get("page")):
        raise ShopifyNormalizationHarnessError("pagination prohibited")
    if catalog.get("ids") or catalog.get("like"):
        raise ShopifyNormalizationHarnessError("bulk or image search prohibited")
    meta = arguments.get("meta")
    profile = ""
    if isinstance(meta, dict):
        agent = meta.get("ucp-agent")
        if isinstance(agent, dict):
            profile = str(agent.get("profile") or "")
    if profile != PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL:
        raise ShopifyNormalizationHarnessError(
            "selected profile is not the exact deployed staging profile"
        )
    endpoint = GLOBAL_CATALOG_ENDPOINT
    if endpoint != "https://catalog.shopify.com/api/ucp/mcp":
        raise ShopifyNormalizationHarnessError("unexpected catalog endpoint")


_RESPONSE_PAGINATION_METADATA_KEYS = frozenset(
    {
        "cursor",
        "end_cursor",
        "has_next_page",
        "next",
        "next_cursor",
        "page",
        "start_cursor",
    }
)


def _response_pagination_metadata_observed(content: Mapping[str, Any]) -> bool:
    """True when the first-page response carries next-page metadata.

    That metadata is ignored. It does not mean PiqSavi requested another page,
    and the cursor is not copied into a later request.
    """

    pagination = content.get("pagination")
    if not isinstance(pagination, dict):
        return False
    return any(key in pagination for key in _RESPONSE_PAGINATION_METADATA_KEYS)


def _variant_ids(product: dict[str, Any]) -> tuple[str, ...]:
    return tuple(_variant_id_set(product))


def _variant_id_set(product: dict[str, Any]) -> frozenset[str]:
    ids: set[str] = set()
    for variant in variants_from_product(product):
        text = _text(variant.get("id"))
        if text:
            ids.add(text)
    return frozenset(ids)


def _availability_counts(offers: list[ShopifyNormalizedOffer]) -> tuple[int, int]:
    """Return non-unknown and unknown availability counts. Unknown is not evidence."""

    unknown = sum(1 for offer in offers if offer.source.availability == ProductAvailability.UNKNOWN)
    return len(offers) - unknown, unknown


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _path_inside_repository(path: Path) -> bool:
    repository = Path(__file__).resolve().parents[2]
    try:
        path.resolve().relative_to(repository)
    except ValueError:
        return False
    return True
