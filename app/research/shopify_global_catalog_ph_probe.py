"""Sprint 32 Shopify Global Catalog PH coverage probe — not certification.

Private-local technical harness helpers for a small, first-page-only
Anonymous query of Shopify Global Catalog with documented PH localization.

This module does not certify Shopify. It does not populate production
provider/certification catalogs. It does not start Sprint 38. It does not
create a product index. Live HTTP belongs in the owner CLI harness and must
not run from this library module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL,
    piqsavi_profile_deployed_for_url,
    trusted_piqsavi_ucp_agent_profile_url,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GLOBAL_CATALOG_ENDPOINT = "https://catalog.shopify.com/api/ucp/mcp"
# Official Shopify-hosted UCP fixture. TECHNICAL TEST ONLY. Not a PiqSavi identity.
TECHNICAL_TEST_AGENT_PROFILE = SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL
AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE = "technical_test_fixture"
AGENT_PROFILE_SOURCE_PIQSAVI = "piqsavi"
AgentProfileSource = Literal["technical_test_fixture", "piqsavi"]
AGENT_PROFILE_USAGE = "TECHNICAL_TEST_ONLY"
AGENT_PROFILE_USAGE_PIQSAVI = "PIQSAVI_OWNED_PROFILE"
AGENT_PROFILE_NOT_PIQSAVI_IDENTITY = True
DEFAULT_AGENT_PROFILE_SOURCE: AgentProfileSource = AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE
LIVE_PIQSAVI_PROFILE_NOT_DEPLOYED_MESSAGE = (
    "PiqSavi UCP profile is not yet deployed/publicly validated. "
    "Deploy and owner-validate the exact selected trusted HTTPS profile URL "
    "before live Shopify negotiation."
)
PIQSAVI_PROFILE_LIFECYCLE_NOTE = (
    "PiqSavi profile lifecycle is environment-specific. "
    "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is true. "
    "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is false. "
    "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is true."
)
PIQSAVI_OWNED_PROFILE_SELECTED_NOTE = "PiqSavi-owned profile selected."
PIQSAVI_PROFILE_DEPLOYED_URL_NOTE = "Exact selected trusted URL is owner-validated as deployed."
PIQSAVI_PROFILE_UNDEPLOYED_URL_NOTE = (
    "Exact selected trusted URL is not owner-validated as deployed."
)
PIQSAVI_PROFILE_SHOPIFY_FETCH_NOTE = "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is true."
PIQSAVI_PROFILE_NOT_CERTIFICATION_NOTE = "Not production certification."
if PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL == TECHNICAL_TEST_AGENT_PROFILE:
    raise RuntimeError("PiqSavi production profile URL must not be Shopify's test fixture")
ANONYMOUS_AUTH_TIER = "Anonymous"
ANONYMOUS_USER_AGENT = "PiqSavi-Sprint32-PH-Coverage-Probe/1.0"
PH_COUNTRY = "PH"
PHP_CURRENCY = "PHP"
CONTEXT_LANGUAGE = "en"
OFFER_VIEW = "offer"
SEARCH_TOOL = "search_catalog"
GET_PRODUCT_TOOL = "get_product"
FORBIDDEN_LOOKUP_TOOL = "lookup_catalog"
MAX_SEARCH_CATALOG_QUERIES = 12
MAX_GET_PRODUCT_VALIDATIONS = 5
FIRST_PAGE_LIMIT = 10
DEFAULT_OUTPUT_DIR = Path("/tmp/piqsavi-shopify-global-ph")
NON_PRODUCTION_FIXTURE_MARKER = "NON_PRODUCTION_FIXTURE"
PRIVATE_LOCAL_LIVE_ARTIFACT = "PRIVATE_LOCAL_LIVE_ARTIFACT"
TECHNICAL_TEST_ONLY = "TECHNICAL_TEST_ONLY"
USEFUL_PH_OFFER = "USEFUL_PH_OFFER"
PARTIAL_PH_RESULT = "PARTIAL_PH_RESULT"
NO_USEFUL_PH_RESULT = "NO_USEFUL_PH_RESULT"
CLASSIFICATIONS = (USEFUL_PH_OFFER, PARTIAL_PH_RESULT, NO_USEFUL_PH_RESULT)
DEFAULT_FIXTURE = (
    REPOSITORY_ROOT
    / "tests/fixtures/shopify_global_catalog_ph_probe/non_production_catalog_responses.json"
)
LIVE_OUTPUT_INSIDE_REPO_MESSAGE = (
    "Live Shopify Global Catalog artifacts must be written outside the repository. "
    "Do not commit live catalog evidence. Use a private local directory such as "
    "/tmp/piqsavi-shopify-global-ph."
)
INFERRED_FIELD_PATHS = (
    "description",
    "options",
    "metadata.attributes",
    "metadata.tech_specs",
    "metadata.top_features",
    "metadata.unique_selling_points",
    "variants[].condition",
)
SOURCE_OFFER_FIELD_PATHS = (
    "product.id",
    "product.url",
    "price_range",
    "variant.id",
    "variant.price",
    "variant.checkout_url",
    "variant.availability",
    "variant.seller",
)
PLACEHOLDER_MARKERS = (
    "example.com",
    "example-running.myshopify.com",
    "example running",
    "lorem ipsum",
    "placeholder",
    "gid://shopify/p/7f3a2b8c1d9e",
    "gid://shopify/shop/987654321",
)
AFFILIATE_FORBIDDEN_REQUEST_KEYS = (
    "catalog_id",
    "saved_catalog_slug",
    "promoted",
    "commission",
    "affiliate",
    "utm_source",
    "utm_medium",
    "utm_campaign",
)


class ProbeLimitError(ValueError):
    """The PH probe exceeded its documented search or get_product budget."""


class ProbeContractError(ValueError):
    """The PH probe refused pagination, bulk lookup, or monetized catalog options."""


class LivePiqsaviProfileNotDeployedError(ProbeContractError):
    """Live Shopify calls cannot use the undeployed PiqSavi agent profile."""


class ProbeResponseError(RuntimeError):
    """Shopify catalog JSON-RPC/MCP returned an error or malformed success."""


class LiveProbeOutputInsideRepositoryError(ValueError):
    """Live catalog artifacts cannot be written inside the git repository."""


class CatalogTransport(Protocol):
    """JSON-RPC catalog transport. Live HTTP is implemented only in the CLI."""

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return the JSON-RPC result object or structured catalog payload."""


@dataclass(frozen=True, slots=True)
class PhProbeIntent:
    query_id: str
    query: str

    def to_dict(self) -> dict[str, str]:
        return {"query_id": self.query_id, "query": self.query}


@dataclass(frozen=True, slots=True)
class MinimizedOfferEvidence:
    product_id: str | None
    variant_id: str | None
    identifiable_product: bool
    seller_identity: str | None
    seller_domain: str | None
    seller_url_present: bool
    checkout_url_present: bool
    product_url_present: bool
    price_present: bool
    price_amount_minor: int | None
    currency: str | None
    availability_present: bool
    availability_available: bool | None
    availability_status: str | None
    ph_query_context_applied: bool
    placeholder_or_test: bool
    usable_for_comparison: bool
    inferred_fields_observed: tuple[str, ...]
    source_offer_fields_observed: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "identifiable_product": self.identifiable_product,
            "seller_identity": self.seller_identity,
            "seller_domain": self.seller_domain,
            "seller_url_present": self.seller_url_present,
            "checkout_url_present": self.checkout_url_present,
            "product_url_present": self.product_url_present,
            "price_present": self.price_present,
            "price_amount_minor": self.price_amount_minor,
            "currency": self.currency,
            "availability_present": self.availability_present,
            "availability_available": self.availability_available,
            "availability_status": self.availability_status,
            "ph_query_context_applied": self.ph_query_context_applied,
            "placeholder_or_test": self.placeholder_or_test,
            "usable_for_comparison": self.usable_for_comparison,
            "inferred_fields_observed": list(self.inferred_fields_observed),
            "source_offer_fields_observed": list(self.source_offer_fields_observed),
        }


@dataclass(frozen=True, slots=True)
class QueryCoverageResult:
    query_id: str
    query: str
    retrieved_at: str | None
    classification: str
    product_returned: bool
    offer_returned: bool
    ships_to_ph_filter_applied: bool
    ph_address_context_applied: bool
    php_currency_context_applied: bool
    offer_view_applied: bool
    identifiable_product: bool
    identifiable_seller: bool
    seller_url_or_domain_present: bool
    price_present: bool
    currency_present: bool
    availability_present: bool
    destination_present: bool
    usable_for_comparison: bool
    inferred_fields_distinguished: bool
    get_product_used: bool
    product_count: int
    offer_count: int
    offers: tuple[MinimizedOfferEvidence, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "retrieved_at": self.retrieved_at,
            "classification": self.classification,
            "product_returned": self.product_returned,
            "offer_returned": self.offer_returned,
            "ships_to_ph_filter_applied": self.ships_to_ph_filter_applied,
            "ph_address_context_applied": self.ph_address_context_applied,
            "php_currency_context_applied": self.php_currency_context_applied,
            "offer_view_applied": self.offer_view_applied,
            "identifiable_product": self.identifiable_product,
            "identifiable_seller": self.identifiable_seller,
            "seller_url_or_domain_present": self.seller_url_or_domain_present,
            "price_present": self.price_present,
            "currency_present": self.currency_present,
            "availability_present": self.availability_present,
            "destination_present": self.destination_present,
            "usable_for_comparison": self.usable_for_comparison,
            "inferred_fields_distinguished": self.inferred_fields_distinguished,
            "get_product_used": self.get_product_used,
            "product_count": self.product_count,
            "offer_count": self.offer_count,
            "offers": [item.to_dict() for item in self.offers],
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class AgentProfileSelection:
    source: str
    url: str
    usage: str
    not_piqsavi_identity: bool
    piqsavi_profile_deployed: bool
    piqsavi_profile_staging_deployed: bool
    piqsavi_profile_production_deployed: bool
    shopify_has_fetched_profile: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_profile_source": self.source,
            "agent_profile": self.url,
            "agent_profile_usage": self.usage,
            "agent_profile_not_piqsavi_identity": self.not_piqsavi_identity,
            "piqsavi_profile_deployed": self.piqsavi_profile_deployed,
            "piqsavi_profile_staging_deployed": self.piqsavi_profile_staging_deployed,
            "piqsavi_profile_production_deployed": self.piqsavi_profile_production_deployed,
            "shopify_has_fetched_piqsavi_profile": self.shopify_has_fetched_profile,
        }


@dataclass(frozen=True, slots=True)
class PhProbeReport:
    generated_at: str
    live: bool
    fixture: bool
    artifact_kind: str
    agent_profile: str
    agent_profile_source: str
    agent_profile_usage: str
    agent_profile_not_piqsavi_identity: bool
    piqsavi_profile_deployed: bool
    piqsavi_profile_staging_deployed: bool
    piqsavi_profile_production_deployed: bool
    shopify_has_fetched_piqsavi_profile: bool
    auth_tier: str
    credentials_required: bool
    endpoint: str
    search_calls: int
    get_product_calls: int
    lookup_catalog_calls: int
    pagination_followed: bool
    bulk_ids_used: bool
    raw_response_persisted: bool
    production_certified: bool
    certifies_shopify: bool
    closes_sprint_32: bool
    starts_sprint_38: bool
    affiliate_or_promoted_placement: bool
    scraping: bool
    environment_mutation: bool
    query_results: tuple[QueryCoverageResult, ...]
    notes: tuple[str, ...] = (
        "Technical PH coverage probe only. Useful PH offers do not certify production.",
        "Anonymous Shopify-hosted fixture profile is TECHNICAL TEST ONLY.",
        PIQSAVI_PROFILE_LIFECYCLE_NOTE,
        "Sprint 32 remains open.",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "live": self.live,
            "fixture": self.fixture,
            "artifact_kind": self.artifact_kind,
            "agent_profile": self.agent_profile,
            "agent_profile_source": self.agent_profile_source,
            "agent_profile_usage": self.agent_profile_usage,
            "agent_profile_not_piqsavi_identity": self.agent_profile_not_piqsavi_identity,
            "piqsavi_profile_deployed": self.piqsavi_profile_deployed,
            "piqsavi_profile_staging_deployed": self.piqsavi_profile_staging_deployed,
            "piqsavi_profile_production_deployed": self.piqsavi_profile_production_deployed,
            "shopify_has_fetched_piqsavi_profile": self.shopify_has_fetched_piqsavi_profile,
            "auth_tier": self.auth_tier,
            "credentials_required": self.credentials_required,
            "endpoint": self.endpoint,
            "search_calls": self.search_calls,
            "get_product_calls": self.get_product_calls,
            "lookup_catalog_calls": self.lookup_catalog_calls,
            "pagination_followed": self.pagination_followed,
            "bulk_ids_used": self.bulk_ids_used,
            "raw_response_persisted": self.raw_response_persisted,
            "production_certified": self.production_certified,
            "certifies_shopify": self.certifies_shopify,
            "closes_sprint_32": self.closes_sprint_32,
            "starts_sprint_38": self.starts_sprint_38,
            "affiliate_or_promoted_placement": self.affiliate_or_promoted_placement,
            "scraping": self.scraping,
            "environment_mutation": self.environment_mutation,
            "query_results": [item.to_dict() for item in self.query_results],
            "notes": list(self.notes),
        }


@dataclass
class ProbeBudget:
    search_calls: int = 0
    get_product_calls: int = 0

    def consume_search(self) -> None:
        if self.search_calls >= MAX_SEARCH_CATALOG_QUERIES:
            raise ProbeLimitError(
                f"PH probe allows at most {MAX_SEARCH_CATALOG_QUERIES} search_catalog queries"
            )
        self.search_calls += 1

    def consume_get_product(self) -> None:
        if self.get_product_calls >= MAX_GET_PRODUCT_VALIDATIONS:
            raise ProbeLimitError(
                f"PH probe allows at most {MAX_GET_PRODUCT_VALIDATIONS} get_product validations"
            )
        self.get_product_calls += 1


@dataclass
class RecordingTransport:
    """In-memory catalog transport for synthetic tests. Does not call Shopify."""

    responses: dict[str, Any]
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if name == FORBIDDEN_LOOKUP_TOOL:
            raise ProbeContractError("lookup_catalog is forbidden for this PH probe")
        catalog = arguments.get("catalog") if isinstance(arguments, dict) else None
        if name == SEARCH_TOOL:
            query = ""
            if isinstance(catalog, dict):
                query = str(catalog.get("query") or "")
            by_query = self.responses.get("search_by_query") or {}
            payload = by_query.get(query) or {"products": []}
            return {"structuredContent": payload}
        if name == GET_PRODUCT_TOOL:
            product_id = ""
            if isinstance(catalog, dict):
                product_id = str(catalog.get("id") or "")
            by_id = self.responses.get("get_product_by_id") or {}
            payload = by_id.get(product_id) or {"product": {}}
            return {"structuredContent": payload}
        raise ProbeContractError(f"unsupported catalog tool {name}")


def load_ph_probe_intents() -> tuple[PhProbeIntent, ...]:
    """Fixed ~12 PH shopping intents. Not a crawl set."""

    return (
        PhProbeIntent("wireless_earbuds", "wireless earbuds"),
        PhProbeIntent("gaming_laptop", "gaming laptop"),
        PhProbeIntent("mechanical_keyboard", "mechanical keyboard"),
        PhProbeIntent("usb_c_charger", "USB-C charger"),
        PhProbeIntent("phone_case", "phone case"),
        PhProbeIntent("portable_power_bank", "portable power bank"),
        PhProbeIntent("skincare_serum", "skincare serum"),
        PhProbeIntent("running_shoes", "running shoes"),
        PhProbeIntent("backpack", "backpack"),
        PhProbeIntent("air_fryer", "air fryer"),
        PhProbeIntent("coffee_grinder", "coffee grinder"),
        PhProbeIntent("home_office_chair", "home office chair"),
    )


def resolve_live_probe_output_dir(path: Path) -> Path:
    return path.expanduser().resolve()


def live_probe_output_is_inside_repository(
    output_dir: Path,
    *,
    repository_root: Path | None = None,
) -> bool:
    resolved = resolve_live_probe_output_dir(output_dir)
    root = resolve_live_probe_output_dir(repository_root or REPOSITORY_ROOT)
    return resolved == root or root in resolved.parents


def assert_live_probe_output_outside_repository(
    output_dir: Path,
    *,
    repository_root: Path | None = None,
) -> Path:
    resolved = resolve_live_probe_output_dir(output_dir)
    if live_probe_output_is_inside_repository(resolved, repository_root=repository_root):
        raise LiveProbeOutputInsideRepositoryError(
            f"{LIVE_OUTPUT_INSIDE_REPO_MESSAGE} Refused: {resolved}"
        )
    return resolved


def select_agent_profile(source: str | None = None) -> AgentProfileSelection:
    """Resolve the probe profile from an explicit source name only.

    Request bodies, query strings, cookies, and shopper input cannot select
    this URL. PiqSavi mode reads the server-owned settings constant.
    """

    selected = source or DEFAULT_AGENT_PROFILE_SOURCE
    if selected == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE:
        return AgentProfileSelection(
            source=AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE,
            url=TECHNICAL_TEST_AGENT_PROFILE,
            usage=AGENT_PROFILE_USAGE,
            not_piqsavi_identity=True,
            piqsavi_profile_deployed=piqsavi_profile_deployed_for_url(TECHNICAL_TEST_AGENT_PROFILE),
            piqsavi_profile_staging_deployed=PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
            piqsavi_profile_production_deployed=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
            shopify_has_fetched_profile=SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
        )
    if selected == AGENT_PROFILE_SOURCE_PIQSAVI:
        url = trusted_piqsavi_ucp_agent_profile_url()
        if url == TECHNICAL_TEST_AGENT_PROFILE:
            raise ProbeContractError(
                "PiqSavi profile source must not resolve to Shopify's test fixture"
            )
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
    raise ProbeContractError(f"unsupported agent profile source {selected}")


def assert_live_piqsavi_profile_unlocked(profile: AgentProfileSelection) -> None:
    """Fail closed unless the exact selected trusted URL is deployed.

    Checks ``piqsavi_profile_deployed_for_url(profile.url)`` against
    server-owned environment constants, not a spoofable selection field.
    Staging may unlock only the exact staging URL. Production remains
    blocked while ``PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED`` is
    false. Arbitrary URLs fail closed. Request, browser, query, cookie,
    and env input cannot flip lifecycle state.
    ``SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE`` is a later independent
    milestone and does not unlock live calls.
    """

    if profile.source != AGENT_PROFILE_SOURCE_PIQSAVI:
        return
    if piqsavi_profile_deployed_for_url(profile.url):
        return
    raise LivePiqsaviProfileNotDeployedError(LIVE_PIQSAVI_PROFILE_NOT_DEPLOYED_MESSAGE)


def agent_profile_meta(profile: AgentProfileSelection | None = None) -> dict[str, Any]:
    selected = profile or select_agent_profile(DEFAULT_AGENT_PROFILE_SOURCE)
    return {"ucp-agent": {"profile": selected.url}}


def ph_catalog_context() -> dict[str, str]:
    return {
        "address_country": PH_COUNTRY,
        "currency": PHP_CURRENCY,
        "language": CONTEXT_LANGUAGE,
    }


def ph_catalog_filters() -> dict[str, Any]:
    return {
        "ships_to": {"country": PH_COUNTRY},
        "available": True,
    }


def _reject_monetized_or_bulk_catalog(catalog: dict[str, Any]) -> None:
    for key in AFFILIATE_FORBIDDEN_REQUEST_KEYS:
        if key in catalog:
            raise ProbeContractError(f"organic PH probe forbids catalog field {key}")
    pagination = catalog.get("pagination")
    if isinstance(pagination, dict) and pagination.get("cursor"):
        raise ProbeContractError("PH probe forbids pagination beyond the first page")
    if catalog.get("ids"):
        raise ProbeContractError("PH probe forbids bulk catalog ids")
    like = catalog.get("like")
    if like:
        raise ProbeContractError("PH probe forbids image/similar-item catalog crawling")


def build_search_catalog_arguments(
    query: str, *, profile: AgentProfileSelection | None = None
) -> dict[str, Any]:
    catalog = {
        "query": query,
        "filters": ph_catalog_filters(),
        "context": ph_catalog_context(),
        "view": OFFER_VIEW,
        "pagination": {"limit": FIRST_PAGE_LIMIT},
    }
    _reject_monetized_or_bulk_catalog(catalog)
    return {"meta": agent_profile_meta(profile), "catalog": catalog}


def build_get_product_arguments(
    product_id: str, *, profile: AgentProfileSelection | None = None
) -> dict[str, Any]:
    if not product_id or "," in product_id:
        raise ProbeContractError("get_product requires exactly one product id")
    catalog = {
        "id": product_id,
        "filters": ph_catalog_filters(),
        "context": ph_catalog_context(),
    }
    _reject_monetized_or_bulk_catalog(catalog)
    return {"meta": agent_profile_meta(profile), "catalog": catalog}


def build_jsonrpc_request(tool_name: str, arguments: dict[str, Any], *, request_id: int) -> dict:
    if tool_name == FORBIDDEN_LOOKUP_TOOL:
        raise ProbeContractError("lookup_catalog is forbidden for this PH probe")
    if tool_name not in {SEARCH_TOOL, GET_PRODUCT_TOOL}:
        raise ProbeContractError(f"unsupported catalog tool {tool_name}")
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": request_id,
        "params": {"name": tool_name, "arguments": arguments},
    }


def anonymous_http_headers() -> dict[str, str]:
    """Anonymous catalog access: JSON only, no Authorization or signatures."""

    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": ANONYMOUS_USER_AGENT,
    }


def _safe_text(value: Any, *, limit: int = 200) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return text if len(text) <= limit else text[:limit]


def _safe_jsonrpc_error_diagnostic(error: Any) -> str:
    if not isinstance(error, dict):
        return "Shopify catalog JSON-RPC error"
    code = error.get("code")
    message = _safe_text(error.get("message"))
    return f"Shopify catalog JSON-RPC error code={code} message={message}"


def _safe_mcp_message_diagnostics(messages: Any) -> str:
    if not isinstance(messages, list):
        return "Shopify catalog MCP tool error"
    parts: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        severity = item.get("type") or item.get("severity")
        content = _safe_text(item.get("content"))
        parts.append(f"code={code} severity={severity} content={content}")
        if len(parts) >= 5:
            break
    if not parts:
        return "Shopify catalog MCP tool error"
    return "Shopify catalog MCP tool error; " + "; ".join(parts)


def validate_catalog_tool_response(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed on JSON-RPC/MCP errors. Do not treat failures as empty catalogs.

    Successful ``structuredContent`` may include non-fatal messages. Those
    warnings are not Shopify error semantics and do not fail the probe.
    """

    if not isinstance(payload, dict):
        raise ProbeResponseError("Shopify catalog response is not a JSON object")
    if payload.get("error") is not None:
        raise ProbeResponseError(_safe_jsonrpc_error_diagnostic(payload.get("error")))
    result: dict[str, Any] | None
    if isinstance(payload.get("result"), dict):
        result = payload["result"]
    elif isinstance(payload.get("structuredContent"), dict):
        result = payload
    else:
        raise ProbeResponseError(
            "Shopify catalog response has neither structuredContent nor a recognized error envelope"
        )
    if result.get("isError") is True:
        content = result.get("structuredContent")
        messages = content.get("messages") if isinstance(content, dict) else None
        raise ProbeResponseError(_safe_mcp_message_diagnostics(messages))
    content = result.get("structuredContent")
    if not isinstance(content, dict):
        raise ProbeResponseError(
            "Shopify catalog response has neither structuredContent nor a recognized error envelope"
        )
    return content


def structured_content_from_result(payload: dict[str, Any] | None) -> dict[str, Any]:
    return validate_catalog_tool_response(payload)


def products_from_catalog_payload(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    content = validate_catalog_tool_response(payload)
    products: list[dict[str, Any]] = []
    raw_products = content.get("products")
    if isinstance(raw_products, list):
        products.extend(item for item in raw_products if isinstance(item, dict))
    product = content.get("product")
    if isinstance(product, dict):
        products.append(product)
    return products


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _absolute_http_url(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    lowered = text.casefold()
    if lowered.startswith("https://") or lowered.startswith("http://"):
        return text
    return None


def _price_amount_minor(price: dict[str, Any]) -> int | None:
    """Shopify/UCP price.amount is integer minor units. Floats are rejected."""

    amount = price.get("amount")
    if isinstance(amount, bool) or amount is None:
        return None
    if isinstance(amount, int):
        return amount
    if isinstance(amount, str):
        stripped = amount.strip()
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def _seller(variant: dict[str, Any]) -> dict[str, Any]:
    seller = variant.get("seller")
    return seller if isinstance(seller, dict) else {}


def _price(source: dict[str, Any]) -> dict[str, Any]:
    price = source.get("price")
    return price if isinstance(price, dict) else {}


def _price_range_min(product: dict[str, Any]) -> dict[str, Any]:
    price_range = product.get("price_range")
    if not isinstance(price_range, dict):
        return {}
    minimum = price_range.get("min")
    return minimum if isinstance(minimum, dict) else {}


def _availability(variant: dict[str, Any]) -> dict[str, Any]:
    availability = variant.get("availability")
    return availability if isinstance(availability, dict) else {}


def _haystack(product: dict[str, Any], variant: dict[str, Any]) -> str:
    seller = _seller(variant)
    parts = [
        _text(product.get("id")),
        _text(product.get("title")),
        _text(product.get("url")),
        _text(variant.get("id")),
        _text(variant.get("title")),
        _text(variant.get("checkout_url")),
        _text(seller.get("id")),
        _text(seller.get("name")),
        _text(seller.get("domain")),
        _text(seller.get("url")),
    ]
    return " ".join(part.casefold() for part in parts if part)


def is_placeholder_or_test_result(product: dict[str, Any], variant: dict[str, Any]) -> bool:
    blob = _haystack(product, variant)
    return any(marker in blob for marker in PLACEHOLDER_MARKERS)


def inferred_fields_observed(product: dict[str, Any], variant: dict[str, Any]) -> tuple[str, ...]:
    observed: list[str] = []
    if product.get("description"):
        observed.append("description")
    if product.get("options"):
        observed.append("options")
    metadata = product.get("metadata") if isinstance(product.get("metadata"), dict) else {}
    for key in ("attributes", "tech_specs", "top_features", "unique_selling_points"):
        if metadata.get(key):
            observed.append(f"metadata.{key}")
    if variant.get("condition"):
        observed.append("variants[].condition")
    return tuple(item for item in INFERRED_FIELD_PATHS if item in observed)


def source_offer_fields_observed(
    product: dict[str, Any], variant: dict[str, Any]
) -> tuple[str, ...]:
    observed: list[str] = []
    if _text(product.get("id")):
        observed.append("product.id")
    if _text(product.get("url")):
        observed.append("product.url")
    if _price_range_min(product):
        observed.append("price_range")
    if _text(variant.get("id")):
        observed.append("variant.id")
    if _price(variant):
        observed.append("variant.price")
    if _text(variant.get("checkout_url")):
        observed.append("variant.checkout_url")
    if _availability(variant):
        observed.append("variant.availability")
    if _seller(variant):
        observed.append("variant.seller")
    return tuple(item for item in SOURCE_OFFER_FIELD_PATHS if item in observed)


def variants_from_product(product: dict[str, Any]) -> list[dict[str, Any]]:
    variants = product.get("variants")
    if isinstance(variants, list):
        return [item for item in variants if isinstance(item, dict)]
    return [{}]


def minimize_offer_evidence(
    product: dict[str, Any], variant: dict[str, Any]
) -> MinimizedOfferEvidence:
    seller = _seller(variant)
    price = _price(variant) or _price_range_min(product)
    availability = _availability(variant)
    product_id = _text(product.get("id"))
    variant_id = _text(variant.get("id"))
    seller_identity = _text(seller.get("name")) or _text(seller.get("id"))
    seller_domain = _text(seller.get("domain"))
    seller_url_present = bool(_absolute_http_url(seller.get("url")))
    checkout_url_present = bool(_absolute_http_url(variant.get("checkout_url")))
    product_url_present = bool(_absolute_http_url(product.get("url")))
    price_amount_minor = _price_amount_minor(price)
    price_present = price_amount_minor is not None
    currency = _text(price.get("currency"))
    availability_present = bool(availability)
    available_value = availability.get("available") if availability_present else None
    if available_value is not None:
        available_value = bool(available_value)
    status = _text(availability.get("status"))
    placeholder = is_placeholder_or_test_result(product, variant)
    identifiable_product = bool(product_id)
    destination = seller_url_present or checkout_url_present or product_url_present
    sale_ready = True
    if availability_present:
        sale_ready = available_value is not False and (status or "in_stock") not in {
            "sold_out",
            "out_of_stock",
            "unavailable",
        }
    usable = (
        identifiable_product
        and price_amount_minor is not None
        and bool(currency)
        and bool(seller_identity)
        and destination
        and sale_ready
        and not placeholder
    )
    return MinimizedOfferEvidence(
        product_id=product_id,
        variant_id=variant_id,
        identifiable_product=identifiable_product,
        seller_identity=seller_identity,
        seller_domain=seller_domain,
        seller_url_present=seller_url_present,
        checkout_url_present=checkout_url_present,
        product_url_present=product_url_present,
        price_present=price_present,
        price_amount_minor=price_amount_minor,
        currency=currency,
        availability_present=availability_present,
        availability_available=available_value,
        availability_status=status,
        ph_query_context_applied=True,
        placeholder_or_test=placeholder,
        usable_for_comparison=usable,
        inferred_fields_observed=inferred_fields_observed(product, variant),
        source_offer_fields_observed=source_offer_fields_observed(product, variant),
    )


def offers_from_products(products: list[dict[str, Any]]) -> tuple[MinimizedOfferEvidence, ...]:
    offers: list[MinimizedOfferEvidence] = []
    for product in products:
        for variant in variants_from_product(product):
            offers.append(minimize_offer_evidence(product, variant))
    return tuple(offers)


def classify_query_offers(offers: tuple[MinimizedOfferEvidence, ...]) -> str:
    real_offers = tuple(item for item in offers if not item.placeholder_or_test)
    if any(item.usable_for_comparison for item in real_offers):
        return USEFUL_PH_OFFER
    if any(item.identifiable_product for item in real_offers):
        return PARTIAL_PH_RESULT
    return NO_USEFUL_PH_RESULT


def _any(offers: tuple[MinimizedOfferEvidence, ...], attr: str) -> bool:
    return any(bool(getattr(item, attr)) for item in offers)


def coverage_flags(offers: tuple[MinimizedOfferEvidence, ...]) -> dict[str, bool]:
    real = tuple(item for item in offers if not item.placeholder_or_test)
    return {
        "product_returned": bool(offers),
        "offer_returned": any(
            item.price_present or item.seller_identity or item.variant_id for item in real
        ),
        "identifiable_product": _any(real, "identifiable_product"),
        "identifiable_seller": any(bool(item.seller_identity) for item in real),
        "seller_url_or_domain_present": any(
            item.seller_url_present or bool(item.seller_domain) for item in real
        ),
        "price_present": _any(real, "price_present"),
        "currency_present": any(bool(item.currency) for item in real),
        "availability_present": _any(real, "availability_present"),
        "destination_present": any(
            item.seller_url_present or item.checkout_url_present or item.product_url_present
            for item in real
        ),
        "usable_for_comparison": any(item.usable_for_comparison for item in real),
        "inferred_fields_distinguished": True,
    }


def select_promising_product_ids(
    products_by_query: dict[str, list[dict[str, Any]]],
    *,
    limit: int = MAX_GET_PRODUCT_VALIDATIONS,
) -> tuple[tuple[str, str], ...]:
    """Choose up to five non-placeholder products across distinct queries.

    First pass selects at most one candidate per query ID: incomplete evidence
    is preferred within a query, then incomplete-query representatives are
    taken in deterministic query order before complete-query representatives.
    Remaining eligible candidates fill leftover slots only after that
    distinct-query pass. Maximum remains five. Selection is not randomized.
    """

    if limit > MAX_GET_PRODUCT_VALIDATIONS:
        raise ProbeLimitError(
            f"PH probe allows at most {MAX_GET_PRODUCT_VALIDATIONS} get_product validations"
        )
    ranked_by_query: list[list[tuple[str, str, bool]]] = []
    seen: set[str] = set()
    for query_id, products in products_by_query.items():
        incomplete: list[tuple[str, str, bool]] = []
        complete: list[tuple[str, str, bool]] = []
        for product in products:
            product_id = _text(product.get("id"))
            if not product_id or product_id in seen:
                continue
            variant = next(iter(variants_from_product(product)), {})
            if is_placeholder_or_test_result(product, variant):
                continue
            evidence = minimize_offer_evidence(product, variant)
            seen.add(product_id)
            pair = (query_id, product_id, not evidence.usable_for_comparison)
            if evidence.usable_for_comparison:
                complete.append(pair)
            else:
                incomplete.append(pair)
        ranked = incomplete + complete
        if ranked:
            ranked_by_query.append(ranked)

    selected: list[tuple[str, str]] = []
    selected_ids: set[str] = set()

    def _take(candidate: tuple[str, str, bool]) -> None:
        query_id, product_id, _incomplete = candidate
        if product_id in selected_ids or len(selected) >= limit:
            return
        selected.append((query_id, product_id))
        selected_ids.add(product_id)

    for ranked in ranked_by_query:
        if len(selected) >= limit:
            break
        representative = next((item for item in ranked if item[2]), None)
        if representative is not None:
            _take(representative)
    for ranked in ranked_by_query:
        if len(selected) >= limit:
            break
        if any(item[2] for item in ranked):
            continue
        _take(ranked[0])

    leftover_incomplete: list[tuple[str, str, bool]] = []
    leftover_complete: list[tuple[str, str, bool]] = []
    for ranked in ranked_by_query:
        for item in ranked:
            if item[1] in selected_ids:
                continue
            if item[2]:
                leftover_incomplete.append(item)
            else:
                leftover_complete.append(item)
    for item in leftover_incomplete + leftover_complete:
        if len(selected) >= limit:
            break
        _take(item)
    return tuple(selected)


def merge_product_detail(
    search_product: dict[str, Any] | None, detail_product: dict[str, Any] | None
) -> dict[str, Any]:
    base = dict(search_product or {})
    detail = dict(detail_product or {})
    if not detail:
        return base
    merged = dict(base)
    for key, value in detail.items():
        if key == "description" or key == "metadata" or key == "media" or key == "options":
            continue
        if value not in (None, "", [], {}):
            merged[key] = value
    if detail.get("variants"):
        merged["variants"] = detail["variants"]
    return merged


def load_probe_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProbeContractError("fixture must be a JSON object")
    marker = str(payload.get("fixture_marker") or "")
    if NON_PRODUCTION_FIXTURE_MARKER not in marker and not payload.get("test_fixture"):
        raise ProbeContractError("refusing a fixture that is not marked non-production")
    return payload


def fixture_transport_from_payload(payload: dict[str, Any]) -> RecordingTransport:
    search_by_query: dict[str, Any] = {}
    by_query_id = payload.get("responses_by_query_id") or {}
    intents = {item.query_id: item.query for item in load_ph_probe_intents()}
    if isinstance(by_query_id, dict):
        for query_id, body in by_query_id.items():
            query = intents.get(str(query_id), str(query_id))
            search_by_query[query] = body
    get_product_by_id = payload.get("get_product_by_id") or {}
    if not isinstance(get_product_by_id, dict):
        get_product_by_id = {}
    return RecordingTransport(
        responses={
            "search_by_query": search_by_query,
            "get_product_by_id": get_product_by_id,
        }
    )


def minimized_artifact_payload(report: PhProbeReport) -> dict[str, Any]:
    payload = report.to_dict()
    payload["technical_test_only"] = True
    payload["not_production_certification"] = True
    payload["not_a_shopify_product_index"] = True
    return payload


def run_ph_coverage_probe(
    *,
    transport: CatalogTransport,
    live: bool,
    retrieved_at: datetime | None = None,
    intents: tuple[PhProbeIntent, ...] | None = None,
    agent_profile_source: str | None = None,
    agent_profile: AgentProfileSelection | None = None,
) -> PhProbeReport:
    selected_intents = intents or load_ph_probe_intents()
    if len(selected_intents) > MAX_SEARCH_CATALOG_QUERIES:
        raise ProbeLimitError(
            f"PH probe allows at most {MAX_SEARCH_CATALOG_QUERIES} search_catalog queries"
        )
    profile = agent_profile or select_agent_profile(
        agent_profile_source or DEFAULT_AGENT_PROFILE_SOURCE
    )
    if live:
        assert_live_piqsavi_profile_unlocked(profile)
    budget = ProbeBudget()
    stamp = (retrieved_at or datetime.now(tz=UTC)).isoformat()
    products_by_query: dict[str, list[dict[str, Any]]] = {}
    query_notes: dict[str, list[str]] = {}
    for intent in selected_intents:
        budget.consume_search()
        arguments = build_search_catalog_arguments(intent.query, profile=profile)
        payload = transport.call_tool(SEARCH_TOOL, arguments)
        products_by_query[intent.query_id] = products_from_catalog_payload(payload)
        query_notes[intent.query_id] = []
        content = structured_content_from_result(payload)
        pagination = content.get("pagination")
        if isinstance(pagination, dict) and pagination.get("has_next_page"):
            query_notes[intent.query_id].append(
                "first_page_only: has_next_page ignored; pagination not followed"
            )

    selected = select_promising_product_ids(products_by_query)
    get_product_queries: set[str] = set()
    for query_id, product_id in selected:
        budget.consume_get_product()
        arguments = build_get_product_arguments(product_id, profile=profile)
        payload = transport.call_tool(GET_PRODUCT_TOOL, arguments)
        detail_products = products_from_catalog_payload(payload)
        detail = detail_products[0] if detail_products else {}
        updated: list[dict[str, Any]] = []
        for product in products_by_query.get(query_id, []):
            if _text(product.get("id")) == product_id:
                updated.append(merge_product_detail(product, detail))
            else:
                updated.append(product)
        products_by_query[query_id] = updated
        get_product_queries.add(query_id)

    results: list[QueryCoverageResult] = []
    for intent in selected_intents:
        products = products_by_query.get(intent.query_id, [])
        offers = offers_from_products(products)
        flags = coverage_flags(offers)
        classification = classify_query_offers(offers)
        results.append(
            QueryCoverageResult(
                query_id=intent.query_id,
                query=intent.query,
                retrieved_at=stamp if live else None,
                classification=classification,
                ships_to_ph_filter_applied=True,
                ph_address_context_applied=True,
                php_currency_context_applied=True,
                offer_view_applied=True,
                get_product_used=intent.query_id in get_product_queries,
                product_count=len(products),
                offer_count=len(offers),
                offers=offers,
                notes=tuple(query_notes.get(intent.query_id, ())),
                **flags,
            )
        )
    return PhProbeReport(
        generated_at=stamp,
        live=live,
        fixture=not live,
        artifact_kind=PRIVATE_LOCAL_LIVE_ARTIFACT if live else NON_PRODUCTION_FIXTURE_MARKER,
        agent_profile=profile.url,
        agent_profile_source=profile.source,
        agent_profile_usage=profile.usage,
        agent_profile_not_piqsavi_identity=profile.not_piqsavi_identity,
        piqsavi_profile_deployed=piqsavi_profile_deployed_for_url(profile.url),
        piqsavi_profile_staging_deployed=PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
        piqsavi_profile_production_deployed=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
        shopify_has_fetched_piqsavi_profile=SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
        auth_tier=ANONYMOUS_AUTH_TIER,
        credentials_required=False,
        endpoint=GLOBAL_CATALOG_ENDPOINT,
        search_calls=budget.search_calls,
        get_product_calls=budget.get_product_calls,
        lookup_catalog_calls=0,
        pagination_followed=False,
        bulk_ids_used=False,
        raw_response_persisted=False,
        production_certified=False,
        certifies_shopify=False,
        closes_sprint_32=False,
        starts_sprint_38=False,
        affiliate_or_promoted_placement=False,
        scraping=False,
        environment_mutation=False,
        query_results=tuple(results),
        notes=_probe_report_notes(profile),
    )


def _probe_report_notes(profile: AgentProfileSelection) -> tuple[str, ...]:
    if profile.source == AGENT_PROFILE_SOURCE_PIQSAVI:
        url_note = (
            PIQSAVI_PROFILE_DEPLOYED_URL_NOTE
            if piqsavi_profile_deployed_for_url(profile.url)
            else PIQSAVI_PROFILE_UNDEPLOYED_URL_NOTE
        )
        return (
            "Technical PH coverage probe only. Useful PH offers do not certify production.",
            PIQSAVI_OWNED_PROFILE_SELECTED_NOTE,
            url_note,
            PIQSAVI_PROFILE_SHOPIFY_FETCH_NOTE,
            PIQSAVI_PROFILE_NOT_CERTIFICATION_NOTE,
            "Sprint 32 remains open.",
        )
    return (
        "Technical PH coverage probe only. Useful PH offers do not certify production.",
        "Anonymous Shopify-hosted fixture profile is TECHNICAL TEST ONLY.",
        PIQSAVI_PROFILE_LIFECYCLE_NOTE,
        "Sprint 32 remains open.",
    )
