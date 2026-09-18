"""Provider-neutral PH public-web shopping benchmark — Sprint 32.

Evaluates whether a retrieval/search provider can surface useful PH retailer
or marketplace product URLs. Does not certify providers. Does not scrape
merchants. Live HTTP is optional and requires owner-supplied credentials
outside this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.domain.entities.public_web_shopping_evidence import (
    SNIPPET_NOT_CANONICAL_PRICE,
    PublicWebShoppingResult,
    ShoppingSourceKind,
    classify_search_hit_as_discovery,
    marketplace_url_is_not_direct_integration,
    offer_promotion_reason,
    shipping_status_from_discovery_text,
)
from app.research.public_web_policy import public_web_provider_policy_audits

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SPEC_PATH = ROOT / "docs/roadmap/evidence/SPRINT_32_PH_PUBLIC_WEB_SHOPPING_BENCHMARK.json"
NON_PRODUCTION_FIXTURE_MARKER = "NON_PRODUCTION_FIXTURE"

_MARKETPLACE_HOSTS = (
    "shopee.ph",
    "shopee.com",
    "lazada.com.ph",
    "lazada.ph",
    "tiktok.com",
    "amazon.com",
    "amazon.com.ph",
)
_RETAILER_HOSTS = (
    "abenson.com",
    "anyshop.ph",
    "apple.com",
    "beyondthebox.ph",
    "digitalwalker.ph",
    "electronica.com.ph",
    "kimstore.com",
    "octagon.com.ph",
    "powermaccenter.com",
    "samsung.com",
    "sony.com.ph",
    "thesmstore.com",
    "villman.com",
)
_MANUFACTURER_HOSTS = (
    "apple.com",
    "samsung.com",
    "sony.com",
    "asus.com",
    "acer.com",
    "lenovo.com",
    "canon.com",
    "lg.com",
    "xiaomi.com",
)
_EDITORIAL_HOSTS = (
    "priceprice.com",
    "gadgetsnow",
    "unbox.ph",
    "yugatech.com",
    "philstar.com",
    "rappler.com",
    "inquirer.net",
)


@dataclass(frozen=True, slots=True)
class PublicWebBenchmarkIntent:
    intent_id: str
    query: str
    category: str
    kind: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "query": self.query,
            "category": self.category,
            "kind": self.kind,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PublicWebResultEvaluation:
    intent_id: str
    provider_key: str
    source_url: str
    merchant_identity: str | None
    product_identity: str | None
    evidence_tier: str
    role: str
    direct_product_url_found: bool
    identifiable_merchant: bool
    identifiable_product: bool
    ph_relevant: bool | None
    php_price_available: bool
    price_tied_to_actual_source: bool
    availability_identifiable: bool
    freshness_fetch_evidence: bool
    outbound_url_usable: bool
    page_source_attribution_preserved: bool
    duplicate: bool
    stale_or_ambiguous: bool
    snippet_only_price: bool
    search_result_versus_product_page: str
    source_kind: ShoppingSourceKind
    marketplace_url_not_direct_integration: bool
    may_enter_evaluated_set: bool
    promotion_refusal: str | None
    shipping_evidence: str
    test_fixture: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "provider_key": self.provider_key,
            "source_url": self.source_url,
            "merchant_identity": self.merchant_identity,
            "product_identity": self.product_identity,
            "evidence_tier": self.evidence_tier,
            "role": self.role,
            "direct_product_url_found": self.direct_product_url_found,
            "identifiable_merchant": self.identifiable_merchant,
            "identifiable_product": self.identifiable_product,
            "ph_relevant": self.ph_relevant,
            "php_price_available": self.php_price_available,
            "price_tied_to_actual_source": self.price_tied_to_actual_source,
            "availability_identifiable": self.availability_identifiable,
            "freshness_fetch_evidence": self.freshness_fetch_evidence,
            "outbound_url_usable": self.outbound_url_usable,
            "page_source_attribution_preserved": self.page_source_attribution_preserved,
            "duplicate": self.duplicate,
            "stale_or_ambiguous": self.stale_or_ambiguous,
            "snippet_only_price": self.snippet_only_price,
            "search_result_versus_product_page": self.search_result_versus_product_page,
            "source_kind": self.source_kind,
            "marketplace_url_not_direct_integration": self.marketplace_url_not_direct_integration,
            "may_enter_evaluated_set": self.may_enter_evaluated_set,
            "promotion_refusal": self.promotion_refusal,
            "shipping_evidence": self.shipping_evidence,
            "test_fixture": self.test_fixture,
            "production_certified": False,
        }


@dataclass(frozen=True, slots=True)
class PublicWebBenchmarkSummary:
    provider_key: str
    intent_count: int
    result_count: int
    discovery_url_count: int
    ph_relevant_count: int
    identifiable_merchant_count: int
    offer_evidence_count: int
    snippet_only_price_count: int
    marketplace_discovery_count: int
    requests_per_query: float
    approximate_cost_usd: float | None
    cost_basis: str
    live: bool
    fixture: bool
    certifies_provider: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "intent_count": self.intent_count,
            "result_count": self.result_count,
            "discovery_url_count": self.discovery_url_count,
            "ph_relevant_count": self.ph_relevant_count,
            "identifiable_merchant_count": self.identifiable_merchant_count,
            "offer_evidence_count": self.offer_evidence_count,
            "snippet_only_price_count": self.snippet_only_price_count,
            "marketplace_discovery_count": self.marketplace_discovery_count,
            "requests_per_query": self.requests_per_query,
            "approximate_cost_usd": self.approximate_cost_usd,
            "cost_basis": self.cost_basis,
            "live": self.live,
            "fixture": self.fixture,
            "certifies_provider": False,
        }


def load_public_web_benchmark_intents(
    path: Path | None = None,
) -> tuple[PublicWebBenchmarkIntent, ...]:
    payload = json.loads((path or BENCHMARK_SPEC_PATH).read_text(encoding="utf-8"))
    if payload.get("production_certified") is True:
        raise ValueError("benchmark spec cannot claim production certification")
    intents = tuple(
        PublicWebBenchmarkIntent(
            intent_id=item["intent_id"],
            query=item["query"],
            category=item["category"],
            kind=item["kind"],
            notes=item.get("notes", ""),
        )
        for item in payload["intents"]
    )
    if len(intents) < 30:
        raise ValueError("PH public-web benchmark requires at least 30 intents")
    return intents


def classify_source_kind(source_url: str) -> ShoppingSourceKind:
    host = (urlparse(source_url).hostname or source_url).casefold()
    if any(token in host for token in _EDITORIAL_HOSTS):
        return "review_editorial"
    if any(token in host for token in _MARKETPLACE_HOSTS):
        return "marketplace"
    if marketplace_url_is_not_direct_integration(source_url):
        return "marketplace"
    if any(token in host for token in _MANUFACTURER_HOSTS):
        return "manufacturer"
    if any(token in host for token in _RETAILER_HOSTS):
        return "direct_retailer"
    return "other"


def merchant_identity_from_url(source_url: str) -> str | None:
    host = urlparse(source_url).hostname
    if not host:
        return None
    host = host.casefold()
    if host.startswith("www."):
        host = host[4:]
    if host in {"brave.com", "tavily.com", "exa.ai"}:
        return None
    return host


def php_price_in_text(text: str) -> str | None:
    lowered = text.casefold()
    if "php" in lowered or "₱" in text or "p " in lowered:
        for token in text.replace(",", "").split():
            stripped = token.strip("₱").strip()
            if stripped.replace(".", "", 1).isdigit() and ("php" in lowered or "₱" in text):
                return token
        return "php_mentioned"
    return None


def evaluate_public_web_hit(
    *,
    intent: PublicWebBenchmarkIntent,
    provider_key: str,
    source_url: str,
    title: str = "",
    snippet: str = "",
    retrieved_at: datetime | None = None,
    provider_result_age: str | None = None,
    duplicate: bool = False,
    test_fixture: bool = True,
) -> tuple[PublicWebShoppingResult, PublicWebResultEvaluation]:
    merchant = merchant_identity_from_url(source_url)
    price_text = php_price_in_text(f"{title} {snippet}")
    result = classify_search_hit_as_discovery(
        query_id=intent.intent_id,
        discovery_provider_id=provider_key,
        source_url=source_url,
        title=title,
        snippet=snippet,
        merchant_identity=merchant,
        page_identity=source_url,
        product_identity=title or None,
        retrieved_at=retrieved_at,
        provider_result_age=provider_result_age,
        source_kind=classify_source_kind(source_url),
        ph_relevant=_ph_relevant(intent.query, source_url, title, snippet),
        php_price_text=price_text,
        availability_text=None,
        outbound_url_usable=bool(source_url.startswith(("http://", "https://"))),
        page_attribution_preserved=bool(source_url),
        duplicate=duplicate,
        search_result_not_product_page=_looks_like_search_or_editorial(source_url),
        contractual_policy="unknown",
        test_fixture=test_fixture,
    )
    evaluation = PublicWebResultEvaluation(
        intent_id=intent.intent_id,
        provider_key=provider_key,
        source_url=source_url,
        merchant_identity=merchant,
        product_identity=title or None,
        evidence_tier=result.evidence_tier,
        role=result.role,
        direct_product_url_found=not result.search_result_not_product_page,
        identifiable_merchant=merchant is not None,
        identifiable_product=bool(title.strip()),
        ph_relevant=result.ph_relevant,
        php_price_available=price_text is not None,
        price_tied_to_actual_source=False,
        availability_identifiable=False,
        freshness_fetch_evidence=retrieved_at is not None or bool(provider_result_age),
        outbound_url_usable=result.outbound_url_usable,
        page_source_attribution_preserved=result.page_attribution_preserved,
        duplicate=duplicate,
        stale_or_ambiguous=result.stale_or_ambiguous,
        snippet_only_price=result.snippet_only_price,
        search_result_versus_product_page=(
            "search_result" if result.search_result_not_product_page else "possible_product_page"
        ),
        source_kind=result.source_kind,
        marketplace_url_not_direct_integration=marketplace_url_is_not_direct_integration(
            source_url
        ),
        may_enter_evaluated_set=result.may_enter_evaluated_set,
        promotion_refusal=offer_promotion_reason(result) or SNIPPET_NOT_CANONICAL_PRICE,
        shipping_evidence=shipping_status_from_discovery_text(snippet),
        test_fixture=test_fixture,
    )
    return result, evaluation


def summarize_public_web_benchmark(
    *,
    provider_key: str,
    intents: tuple[PublicWebBenchmarkIntent, ...],
    evaluations: tuple[PublicWebResultEvaluation, ...],
    requests_made: int,
    live: bool,
    fixture: bool,
) -> PublicWebBenchmarkSummary:
    intent_count = len(intents)
    requests_per_query = (requests_made / intent_count) if intent_count else 0.0
    cost, basis = approximate_documented_cost_usd(provider_key, requests_made)
    return PublicWebBenchmarkSummary(
        provider_key=provider_key,
        intent_count=intent_count,
        result_count=len(evaluations),
        discovery_url_count=sum(1 for item in evaluations if item.outbound_url_usable),
        ph_relevant_count=sum(1 for item in evaluations if item.ph_relevant),
        identifiable_merchant_count=sum(1 for item in evaluations if item.identifiable_merchant),
        offer_evidence_count=sum(1 for item in evaluations if item.may_enter_evaluated_set),
        snippet_only_price_count=sum(1 for item in evaluations if item.snippet_only_price),
        marketplace_discovery_count=sum(
            1 for item in evaluations if item.source_kind == "marketplace"
        ),
        requests_per_query=requests_per_query,
        approximate_cost_usd=cost,
        cost_basis=basis,
        live=live,
        fixture=fixture,
    )


def approximate_documented_cost_usd(
    provider_key: str, requests_made: int
) -> tuple[float | None, str]:
    """Approximate cost from published public pricing. Not an invoice."""

    audits = {item.provider_key: item for item in public_web_provider_policy_audits()}
    audit = audits.get(provider_key)
    basis_prefix = "public documentation 2026-09-18; not an invoice; "
    if provider_key == "brave_search":
        return round(requests_made * 5.0 / 1000.0, 4), (
            basis_prefix + "Brave Search prepaid $5 / 1,000 requests"
        )
    if provider_key == "tavily_search":
        return 0.0 if requests_made <= 1000 else round((requests_made - 1000) * 0.008, 4), (
            basis_prefix + "Tavily Researcher 1,000 free credits/month; basic search = 1 credit; "
            "pay-as-you-go $0.008/credit after"
        )
    if provider_key == "exa_search":
        return round(requests_made * 7.0 / 1000.0, 4), (
            basis_prefix + "Exa Search $7 / 1,000 requests (up to 10 results)"
        )
    if audit is None:
        return None, basis_prefix + "provider pricing unknown"
    return None, basis_prefix + audit.pricing_public_facts


def credential_env_name(provider_key: str) -> str:
    return {
        "brave_search": "BRAVE_SEARCH_API_KEY",
        "tavily_search": "TAVILY_API_KEY",
        "exa_search": "EXA_API_KEY",
    }[provider_key]


def owner_action_required(provider_key: str) -> dict[str, str]:
    env_name = credential_env_name(provider_key)
    signup = {
        "brave_search": (
            "Create a Brave Search API account at "
            "https://api-dashboard.search.brave.com/ and copy the subscription "
            "token. Prefer a free/testing plan. Do not buy a plan unless the "
            "owner chooses to."
        ),
        "tavily_search": (
            "Create a Tavily account at https://www.tavily.com/ and copy the "
            "API key from the dashboard. Free Researcher plan is 1,000 "
            "credits/month with no credit card."
        ),
        "exa_search": (
            "Create an Exa account at https://dashboard.exa.ai/ and copy the "
            "API key. New accounts include documented free credits."
        ),
    }[provider_key]
    return {
        "owner_action_required": "yes",
        "provider": provider_key,
        "signup_step": signup,
        "credential_needed": env_name,
        "store_where": (
            "Owner-managed secret store, later `dealbrain/<env>/` Secrets Manager "
            f"leaf if production wiring is approved. Local live benchmark: export {env_name} "
            "in the shell only. Never paste the secret into chat, Git, Cursor prompts, "
            "or source control."
        ),
    }


def _ph_relevant(query: str, source_url: str, title: str, snippet: str) -> bool | None:
    blob = f"{query} {source_url} {title} {snippet}".casefold()
    tokens = (
        "philippines",
        ".ph",
        "manila",
        "cebu",
        "php",
        "₱",
        "shopee.ph",
        "lazada.com.ph",
        "piqsavi",
    )
    if any(token in blob for token in tokens):
        return True
    return None


def _looks_like_search_or_editorial(source_url: str) -> bool:
    host = (urlparse(source_url).hostname or "").casefold()
    path = urlparse(source_url).path.casefold()
    if classify_source_kind(source_url) == "review_editorial":
        return True
    if any(token in path for token in ("/search", "/tag/", "/blog", "/news")):
        return True
    return host.endswith("google.com") or host.endswith("bing.com") or "brave.com" in host


def assert_non_production_fixture(payload: dict[str, Any]) -> None:
    marker = str(payload.get("fixture_marker", ""))
    if NON_PRODUCTION_FIXTURE_MARKER not in marker and payload.get("test_fixture") is not True:
        raise ValueError("live-looking payloads cannot be used as production evidence")
    if payload.get("production_certified") is True:
        raise ValueError("fixtures cannot claim production certification")
