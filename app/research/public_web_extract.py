"""Tavily Extract technical Level-B benchmark helpers — Sprint 32.

Evaluates whether official Tavily Extract can retrieve enough current,
attributable page content from direct Philippine retailer/product URLs to
create TECHNICAL Level-B shopping-evidence candidates.

This module does not certify Tavily. It does not certify any retailer.
It does not create offer evidence. It does not close Sprint 32. It does
not start Sprint 38. It does not fetch merchant pages.

Live HTTP belongs in the owner harness and may call only the official
Tavily Extract API. Live artifacts are PRIVATE/LOCAL only: Tavily terms
restrict disclosure of performance information or analysis relating to
its Services.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.domain.entities.offer_economics import CanonicalMoneyLine
from app.domain.entities.public_web_shopping_evidence import (
    LEVEL_B,
    LEVEL_D,
    SNIPPET_NOT_CANONICAL_PRICE,
    PublicWebProvenance,
    PublicWebShoppingResult,
    ShoppingSourceKind,
    offer_promotion_reason,
    refuse_snippet_price_line,
    shipping_status_from_discovery_text,
    unknown_money_line,
)
from app.domain.entities.research_execution import CapabilityPolicyState
from app.research.public_web_benchmark import (
    classify_source_kind,
    merchant_identity_from_url,
)
from app.research.public_web_policy import tavily_search_policy_audit

MAX_EXTRACT_SAMPLE_URLS = 15
TAVILY_EXTRACT_MAX_URLS_PER_REQUEST = 20
DEFAULT_EXTRACT_DEPTH = "basic"
TAVILY_EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
DEFAULT_EXTRACT_OUTPUT_DIR = Path("/tmp/piqsavi-tavily-extract-ph")
DEFAULT_SEARCH_REPORT_PATH = Path("/tmp/piqsavi-tavily-ph/tavily_search.json")
PRIVATE_LOCAL_LIVE_ARTIFACT = "PRIVATE_LOCAL_LIVE_ARTIFACT"
TECHNICAL_LEVEL_B_CANDIDATE = "TECHNICAL_LEVEL_B_CANDIDATE"
TECHNICAL_LEVEL_B_NOT_OFFER_EVIDENCE = "technical_level_b_candidate_is_not_offer_evidence"
MISSING_SEARCH_REPORT_MESSAGE = (
    "Prior Tavily Search report is absent. Rerun the search benchmark first. "
    "Do not fabricate URLs. Example: uv run python scripts/public_web_ph_benchmark.py "
    "--provider tavily_search --live --output-dir /tmp/piqsavi-tavily-ph"
)
PREFERRED_SOURCE_KINDS = frozenset({"direct_retailer", "manufacturer", "authorized_reseller"})
SOURCE_SITE_POLICY_DEFAULT: CapabilityPolicyState = "unknown"

_AMBIGUOUS_PRICE_MARKERS = (
    "installment",
    "instalment",
    "monthly",
    "/mo",
    "per month",
    "x months",
    "months to pay",
    "downpayment",
    "down payment",
    "msrp",
    "srp",
    "recommended retail",
    "voucher",
    "coupon",
    "% off",
    "percent off",
    "discount",
    "you save",
    "save php",
    "save ₱",
    "bundle",
    "accessory",
    "was php",
    "was ₱",
    "before php",
    "crossed",
    "strikethrough",
)
_STALE_MARKERS = (
    "page not found",
    "this listing has ended",
    "no longer available",
    "product unavailable",
    "404",
)
_AVAILABILITY_MARKERS = (
    "in stock",
    "out of stock",
    "sold out",
    "pre-order",
    "preorder",
    "available now",
    "availability",
)
_SHIPPING_MARKERS = ("shipping", "delivery", "ships to", "ship to")
_STRUCTURED_MARKERS = (
    "sku",
    "model number",
    "add to cart",
    "add to bag",
    "buy now",
    "specifications",
    "product details",
)
_PHP_AMOUNT = re.compile(
    r"(?:php|₱)\s*[\d,]+(?:\.\d{1,2})?|[\d,]+(?:\.\d{1,2})?\s*(?:php)",
    re.IGNORECASE,
)
_CATEGORY_PREFIXES = frozenset(
    {
        "search",
        "tag",
        "blog",
        "news",
        "category",
        "categories",
        "collection",
        "collections",
        "catalog",
        "c",
    }
)


class MissingSearchReportError(FileNotFoundError):
    """Owner must rerun the Tavily Search benchmark. URLs are not invented."""


class ExtractSampleError(ValueError):
    """Extract sample cannot be built from the supplied search report."""


@dataclass(frozen=True, slots=True)
class ExtractCandidateHit:
    source_url: str
    merchant_identity: str | None
    product_identity: str | None
    title: str
    category: str
    source_kind: ShoppingSourceKind
    intent_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "merchant_identity": self.merchant_identity,
            "product_identity": self.product_identity,
            "title": self.title,
            "category": self.category,
            "source_kind": self.source_kind,
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class PriceCandidateSignal:
    price_candidate_detected: bool
    price_appears_attributable: bool
    php_price_like_text_present: bool
    ambiguity_reason: str | None
    matched_text: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_candidate_detected": self.price_candidate_detected,
            "price_appears_attributable": self.price_appears_attributable,
            "php_price_like_text_present": self.php_price_like_text_present,
            "ambiguity_reason": self.ambiguity_reason,
            "matched_text": self.matched_text,
        }


@dataclass(frozen=True, slots=True)
class SourcePolicySeparation:
    """Four rights questions that must not be collapsed.

    A. retrieval technically possible
    B. Tavily API use under Tavily account/terms
    C. source-site content/use rights
    D. production capability policy

    A + B does not imply C or D.
    """

    retrieval_technically_possible: bool
    tavily_api_use_state: CapabilityPolicyState
    source_site_content_rights: CapabilityPolicyState
    production_capability_policy: CapabilityPolicyState

    def __post_init__(self) -> None:
        for state in (
            self.tavily_api_use_state,
            self.source_site_content_rights,
            self.production_capability_policy,
        ):
            if state not in {"allowed", "restricted", "prohibited", "unknown"}:
                raise ValueError("policy state is unknown and fails closed")

    @property
    def policy_allowed(self) -> bool:
        return (
            self.source_site_content_rights == "allowed"
            and self.production_capability_policy == "allowed"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_technically_possible": self.retrieval_technically_possible,
            "tavily_api_use_state": self.tavily_api_use_state,
            "source_site_content_rights": self.source_site_content_rights,
            "production_capability_policy": self.production_capability_policy,
            "policy_allowed": self.policy_allowed,
            "a_plus_b_does_not_imply_c_or_d": True,
        }


@dataclass(frozen=True, slots=True)
class TechnicalExtractEvaluation:
    source_url: str
    merchant_identity: str | None
    retrieved_at: datetime | None
    extraction_succeeded: bool
    extracted_content_length: int
    content_hash: str | None
    page_title: str | None
    product_identity: str | None
    price_signal: PriceCandidateSignal
    availability_text_present: bool
    shipping_text_present: bool
    product_structured_evidence_present: bool
    technical_level_b_candidate: bool
    technical_level_b_reason: str
    stale_or_ambiguous: bool
    offer_evidence: bool
    may_enter_evaluated_set: bool
    policy: SourcePolicySeparation
    shipping_evidence: str
    canonical_price_created: bool
    promotion_refusal: str | None
    test_fixture: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "merchant_identity": self.merchant_identity,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "extraction_succeeded": self.extraction_succeeded,
            "extracted_content_length": self.extracted_content_length,
            "content_hash": self.content_hash,
            "page_title": self.page_title,
            "product_identity": self.product_identity,
            "php_price_like_text_present": self.price_signal.php_price_like_text_present,
            "price_candidate_detected": self.price_signal.price_candidate_detected,
            "price_appears_attributable": self.price_signal.price_appears_attributable,
            "price_ambiguity_reason": self.price_signal.ambiguity_reason,
            "availability_text_present": self.availability_text_present,
            "shipping_text_present": self.shipping_text_present,
            "product_structured_evidence_present": self.product_structured_evidence_present,
            "technical_level_b_candidate": self.technical_level_b_candidate,
            "technical_level_b_reason": self.technical_level_b_reason,
            "stale_or_ambiguous": self.stale_or_ambiguous,
            "offer_evidence": False,
            "may_enter_evaluated_set": False,
            "policy_allowed": self.policy.policy_allowed,
            "source_site_contractual_policy": self.policy.source_site_content_rights,
            "shipping_evidence": self.shipping_evidence,
            "canonical_price_created": False,
            "promotion_refusal": self.promotion_refusal,
            "test_fixture": self.test_fixture,
            "production_certified": False,
            **self.policy.to_dict(),
        }


def documented_basic_extract_credit_max(url_count: int) -> int:
    """Conservative documented credit ceiling if every basic extraction succeeds.

    Official Tavily pricing: basic extract is 1 API credit per 5 successful
    extractions. Failed extractions are not charged. This is methodology, not
    an invoice and not a live performance report.
    """

    if url_count <= 0:
        return 0
    if url_count > MAX_EXTRACT_SAMPLE_URLS:
        raise ExtractSampleError(
            f"first extract benchmark max is {MAX_EXTRACT_SAMPLE_URLS} URLs"
        )
    return (url_count + 4) // 5


def default_source_policy_separation(
    *,
    retrieval_technically_possible: bool,
) -> SourcePolicySeparation:
    audit = tavily_search_policy_audit()
    return SourcePolicySeparation(
        retrieval_technically_possible=retrieval_technically_possible,
        tavily_api_use_state=audit.topic_state("api_use"),
        source_site_content_rights=SOURCE_SITE_POLICY_DEFAULT,
        production_capability_policy="unknown",
    )


def is_excluded_marketplace_url(source_url: str) -> bool:
    host = (urlparse(source_url).hostname or source_url).casefold()
    return classify_source_kind(source_url) == "marketplace" or any(
        token in host
        for token in ("shopee.", "lazada.", "tiktok.com", "amazon.")
    )


def looks_like_search_or_category_page(source_url: str) -> bool:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.casefold()
    if classify_source_kind(source_url) == "review_editorial":
        return True
    if any(token in path for token in ("/search", "/tag/", "/blog/", "/news/")):
        return True
    parts = [part for part in path.split("/") if part]
    if parts and parts[0] in _CATEGORY_PREFIXES:
        return True
    return host.endswith("google.com") or host.endswith("bing.com") or "brave.com" in host


def content_sha256(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def page_title_from_extracted_content(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:200]
    return None


def detect_price_candidate(text: str) -> PriceCandidateSignal:
    """Mark PHP-like text without creating a canonical listing price.

    Ambiguous installment, voucher, MSRP, crossed-out, bundle, and accessory
    amounts are not attributable current listing evidence.
    """

    if not text.strip():
        return PriceCandidateSignal(False, False, False, None, None)
    php_like = "php" in text.casefold() or "₱" in text
    matches = list(_PHP_AMOUNT.finditer(text))
    if not matches:
        return PriceCandidateSignal(False, False, php_like, None, None)
    attributable: str | None = None
    ambiguous_reason: str | None = None
    first_match = matches[0].group(0)
    for match in matches:
        window_start = max(0, match.start() - 80)
        window_end = min(len(text), match.end() + 80)
        window = text[window_start:window_end].casefold()
        marker = next((item for item in _AMBIGUOUS_PRICE_MARKERS if item in window), None)
        if marker is None:
            attributable = match.group(0)
            break
        ambiguous_reason = f"ambiguous_numeric_text:{marker}"
    if attributable is not None:
        return PriceCandidateSignal(True, True, True, None, attributable)
    return PriceCandidateSignal(True, False, True, ambiguous_reason, first_match)


def refuse_uncertified_extract_price(result: PublicWebShoppingResult) -> CanonicalMoneyLine:
    """Extracted PHP-like text is not canonical listing price."""

    return refuse_snippet_price_line(result)


def load_search_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MissingSearchReportError(f"{MISSING_SEARCH_REPORT_MESSAGE} Missing file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ExtractSampleError("search report must be a JSON object")
    return payload


def hits_from_search_report(payload: dict[str, Any]) -> tuple[ExtractCandidateHit, ...]:
    rows = _evaluation_rows(payload)
    hits: list[ExtractCandidateHit] = []
    for row in rows:
        url = str(row.get("source_url") or row.get("url") or "").strip()
        if not url:
            continue
        title = str(row.get("title") or row.get("product_identity") or "")
        intent_id = str(row.get("intent_id") or "")
        source_kind = row.get("source_kind")
        if source_kind not in {
            "manufacturer",
            "direct_retailer",
            "marketplace",
            "authorized_reseller",
            "review_editorial",
            "other",
        }:
            source_kind = classify_source_kind(url)
        hits.append(
            ExtractCandidateHit(
                source_url=url,
                merchant_identity=row.get("merchant_identity") or merchant_identity_from_url(url),
                product_identity=row.get("product_identity") or title or None,
                title=title,
                category=_category_from_intent(intent_id, row.get("category")),
                source_kind=source_kind,
                intent_id=intent_id,
            )
        )
    return tuple(hits)


def select_extract_sample(
    hits: tuple[ExtractCandidateHit, ...],
    *,
    max_urls: int = MAX_EXTRACT_SAMPLE_URLS,
) -> tuple[ExtractCandidateHit, ...]:
    """Select a small first-pass direct-retailer extract sample.

    Marketplace, editorial, search/category, and duplicate URLs are excluded.
    The sample never exceeds ``MAX_EXTRACT_SAMPLE_URLS``.
    """

    if max_urls > MAX_EXTRACT_SAMPLE_URLS:
        raise ExtractSampleError(
            f"first extract benchmark max is {MAX_EXTRACT_SAMPLE_URLS} URLs"
        )
    if max_urls > TAVILY_EXTRACT_MAX_URLS_PER_REQUEST:
        raise ExtractSampleError(
            f"Tavily Extract documents a max of {TAVILY_EXTRACT_MAX_URLS_PER_REQUEST} "
            "URLs per request"
        )
    eligible: list[ExtractCandidateHit] = []
    seen: set[str] = set()
    for hit in hits:
        url = hit.source_url.strip()
        if not url or url in seen:
            continue
        if not url.startswith(("http://", "https://")):
            continue
        if is_excluded_marketplace_url(url):
            continue
        if classify_source_kind(url) == "review_editorial":
            continue
        if looks_like_search_or_category_page(url):
            continue
        seen.add(url)
        kind = classify_source_kind(url)
        eligible.append(
            ExtractCandidateHit(
                source_url=url,
                merchant_identity=hit.merchant_identity or merchant_identity_from_url(url),
                product_identity=hit.product_identity,
                title=hit.title,
                category=hit.category or "uncategorized",
                source_kind=kind,
                intent_id=hit.intent_id,
            )
        )
    preferred = [item for item in eligible if item.source_kind in PREFERRED_SOURCE_KINDS]
    others = [item for item in eligible if item.source_kind not in PREFERRED_SOURCE_KINDS]
    selected = _diversify(preferred, max_urls)
    if len(selected) < max_urls:
        selected.extend(
            _diversify(
                others,
                max_urls - len(selected),
                exclude_urls={item.source_url for item in selected},
            )
        )
    return tuple(selected[:max_urls])


def select_extract_sample_from_report(
    path: Path,
    *,
    max_urls: int = MAX_EXTRACT_SAMPLE_URLS,
) -> tuple[ExtractCandidateHit, ...]:
    payload = load_search_report(path)
    selected = select_extract_sample(hits_from_search_report(payload), max_urls=max_urls)
    if not selected:
        raise ExtractSampleError(
            "No eligible direct retailer/manufacturer product URLs were found in "
            f"{path}. Marketplace, editorial, and search/category pages are "
            "excluded from the first extract benchmark."
        )
    return selected


def evaluate_extracted_page(
    *,
    source_url: str,
    raw_content: str | None,
    retrieved_at: datetime | None,
    extraction_succeeded: bool,
    merchant_identity: str | None = None,
    seed_product_identity: str | None = None,
    source_site_policy: CapabilityPolicyState = SOURCE_SITE_POLICY_DEFAULT,
    test_fixture: bool = True,
) -> TechnicalExtractEvaluation:
    content = raw_content or ""
    succeeded = bool(extraction_succeeded and source_url and content.strip())
    merchant = merchant_identity or merchant_identity_from_url(source_url)
    title = page_title_from_extracted_content(content) if succeeded else None
    product_identity = title or seed_product_identity
    price_signal = detect_price_candidate(content) if succeeded else PriceCandidateSignal(
        False, False, False, None, None
    )
    lowered = content.casefold()
    availability_present = succeeded and any(token in lowered for token in _AVAILABILITY_MARKERS)
    shipping_present = succeeded and any(token in lowered for token in _SHIPPING_MARKERS)
    structured_present = succeeded and any(token in lowered for token in _STRUCTURED_MARKERS)
    stale = succeeded and (
        any(token in lowered for token in _STALE_MARKERS) or len(content.strip()) < 40
    )
    candidate, reason = technical_level_b_decision(
        extraction_succeeded=succeeded,
        source_url=source_url,
        merchant_identity=merchant,
        product_identity=product_identity,
        retrieved_at=retrieved_at,
        price_appears_attributable=price_signal.price_appears_attributable,
        stale_or_ambiguous=stale,
    )
    policy = default_source_policy_separation(retrieval_technically_possible=succeeded)
    if source_site_policy != SOURCE_SITE_POLICY_DEFAULT:
        policy = SourcePolicySeparation(
            retrieval_technically_possible=policy.retrieval_technically_possible,
            tavily_api_use_state=policy.tavily_api_use_state,
            source_site_content_rights=source_site_policy,
            production_capability_policy=policy.production_capability_policy,
        )
    shopping = _shopping_result_from_extract(
        source_url=source_url,
        merchant=merchant,
        product_identity=product_identity,
        title=title or "",
        retrieved_at=retrieved_at,
        succeeded=succeeded,
        candidate=candidate,
        price_signal=price_signal,
        stale=stale,
        contractual_policy="unknown",
        test_fixture=test_fixture,
    )
    return TechnicalExtractEvaluation(
        source_url=source_url,
        merchant_identity=merchant,
        retrieved_at=retrieved_at,
        extraction_succeeded=succeeded,
        extracted_content_length=len(content) if succeeded else 0,
        content_hash=content_sha256(content) if succeeded else None,
        page_title=title,
        product_identity=product_identity,
        price_signal=price_signal,
        availability_text_present=availability_present,
        shipping_text_present=shipping_present,
        product_structured_evidence_present=structured_present,
        technical_level_b_candidate=candidate,
        technical_level_b_reason=reason,
        stale_or_ambiguous=stale,
        offer_evidence=False,
        may_enter_evaluated_set=False,
        policy=policy,
        shipping_evidence=shipping_status_from_discovery_text(content),
        canonical_price_created=False,
        promotion_refusal=offer_promotion_reason(shopping)
        or TECHNICAL_LEVEL_B_NOT_OFFER_EVIDENCE,
        test_fixture=test_fixture,
    )


def technical_level_b_decision(
    *,
    extraction_succeeded: bool,
    source_url: str,
    merchant_identity: str | None,
    product_identity: str | None,
    retrieved_at: datetime | None,
    price_appears_attributable: bool,
    stale_or_ambiguous: bool,
) -> tuple[bool, str]:
    """TECHNICAL Level-B candidate only. Not certified offer evidence."""

    if not extraction_succeeded:
        return False, "extract_failed"
    if not source_url.strip():
        return False, "source_url_missing"
    if not merchant_identity:
        return False, "merchant_identity_not_identifiable"
    if not (product_identity or "").strip():
        return False, "product_or_page_identity_not_identifiable"
    if retrieved_at is None:
        return False, "retrieval_timestamp_missing"
    if not price_appears_attributable:
        return False, "price_not_attributable_to_product_source"
    if stale_or_ambiguous:
        return False, "stale_or_ambiguous"
    return True, TECHNICAL_LEVEL_B_CANDIDATE


def unknown_shipping_money_line() -> CanonicalMoneyLine:
    return unknown_money_line(kind="shipping")


def assert_artifact_has_no_secrets(payload: dict[str, Any], secrets: tuple[str, ...]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for secret in secrets:
        if secret and secret in serialized:
            raise RuntimeError("refusing to write an artifact that contains a credential")
    if re.search(r"tvly-[A-Za-z0-9]", serialized):
        raise RuntimeError("refusing to write an artifact that looks like a Tavily key")
    if "X-Subscription-Token" in serialized:
        raise RuntimeError("refusing to write an artifact that contains request headers")
    if re.search(r"Authorization:\s*Bearer", serialized, re.IGNORECASE):
        raise RuntimeError("refusing to write an artifact that contains request headers")


def _evaluation_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("evaluations"), list):
        return [row for row in payload["evaluations"] if isinstance(row, dict)]
    reports = payload.get("reports")
    if isinstance(reports, list):
        rows: list[dict[str, Any]] = []
        for report in reports:
            if not isinstance(report, dict):
                continue
            for row in report.get("evaluations", []):
                if isinstance(row, dict):
                    rows.append(row)
        if rows:
            return rows
    by_intent = payload.get("results_by_intent")
    if isinstance(by_intent, dict):
        rows = []
        for intent_id, hits in by_intent.items():
            if not isinstance(hits, list):
                continue
            for row in hits:
                if isinstance(row, dict):
                    rows.append({**row, "intent_id": intent_id})
        return rows
    raise ExtractSampleError(
        "search report has no evaluations or results_by_intent; rerun the "
        "Tavily Search benchmark"
    )


def _category_from_intent(intent_id: str, explicit: Any = None) -> str:
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    parts = intent_id.split("-")
    if len(parts) >= 3 and parts[0] == "ph":
        return parts[1]
    return "uncategorized"


def _diversify(
    hits: list[ExtractCandidateHit],
    limit: int,
    *,
    exclude_urls: set[str] | None = None,
) -> list[ExtractCandidateHit]:
    buckets: dict[str, list[ExtractCandidateHit]] = {}
    for hit in hits:
        if exclude_urls and hit.source_url in exclude_urls:
            continue
        buckets.setdefault(hit.category, []).append(hit)
    selected: list[ExtractCandidateHit] = []
    while len(selected) < limit:
        progressed = False
        for category in sorted(buckets):
            if buckets[category] and len(selected) < limit:
                selected.append(buckets[category].pop(0))
                progressed = True
        if not progressed:
            break
    return selected


def _shopping_result_from_extract(
    *,
    source_url: str,
    merchant: str | None,
    product_identity: str | None,
    title: str,
    retrieved_at: datetime | None,
    succeeded: bool,
    candidate: bool,
    price_signal: PriceCandidateSignal,
    stale: bool,
    contractual_policy: CapabilityPolicyState,
    test_fixture: bool,
) -> PublicWebShoppingResult:
    return PublicWebShoppingResult(
        query_id="tavily-extract-ph",
        provenance=PublicWebProvenance(
            discovery_provider_id="tavily_search",
            source_url=source_url or "https://invalid.example/missing",
            merchant_identity=merchant,
            page_identity=source_url or None,
            product_identity=product_identity,
            retrieved_at=retrieved_at,
            contractual_policy=contractual_policy,
            notes="technical extract evaluation; not certified offer evidence",
        ),
        title=title,
        snippet="",
        evidence_tier=LEVEL_B if candidate else LEVEL_D,
        source_kind=classify_source_kind(source_url) if source_url else "other",
        role="discovery_only",
        php_price_text=price_signal.matched_text,
        price_tied_to_source=price_signal.price_appears_attributable,
        freshness_evidence=retrieved_at is not None and succeeded,
        outbound_url_usable=source_url.startswith(("http://", "https://")),
        page_attribution_preserved=bool(source_url),
        stale_or_ambiguous=stale,
        snippet_only_price=not succeeded,
        search_result_not_product_page=not succeeded,
        test_fixture=test_fixture,
    )
