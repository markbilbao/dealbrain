"""Non-secret public-web provider policy audit — Sprint 32.

Engineering interpretation of published official documentation only.
Not professional legal approval. Ambiguity stays UNKNOWN.
Does not certify Brave, Tavily, or Exa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.domain.entities.research_execution import CapabilityPolicyState

POLICY_REVIEW_DATE = date(2026, 9, 18)

# Brave Web Search `country` is a documented 2-character enum, but public docs
# only show a truncated list ("AR AU AT +35 more") plus examples US and DE.
# PH is not in that visible published set. Do not send `country=PH`.
BRAVE_WEB_SEARCH_COUNTRY_ENUM_COMPLETE = False
BRAVE_WEB_SEARCH_VISIBLE_COUNTRY_CODES = frozenset({"AR", "AU", "AT", "US", "DE"})


def brave_ph_country_parameter_verified() -> bool:
    """False until the published Brave `country` enum is recorded as including PH."""

    return BRAVE_WEB_SEARCH_COUNTRY_ENUM_COMPLETE and "PH" in BRAVE_WEB_SEARCH_VISIBLE_COUNTRY_CODES


def brave_web_search_request_params(
    query: str,
    *,
    count: int = 10,
    country: str | None = None,
) -> dict[str, str | int]:
    """Build Brave Web Search params without guessing unverified enum values.

    PH shopping intent belongs in the query text. ``country`` is omitted unless
    the published enum has been recorded as complete and the requested code is
    in that recorded set.
    """

    params: dict[str, str | int] = {"q": query, "count": count}
    if country is None or not str(country).strip():
        return params
    code = str(country).strip().upper()
    if not BRAVE_WEB_SEARCH_COUNTRY_ENUM_COMPLETE:
        raise ValueError(
            "Brave Web Search country enum is incomplete in reviewed public docs; "
            f"refusing to send country={code!r}"
        )
    if code not in BRAVE_WEB_SEARCH_VISIBLE_COUNTRY_CODES:
        raise ValueError(f"Brave country {code!r} is not in the recorded documented enum")
    params["country"] = code
    return params


@dataclass(frozen=True, slots=True)
class PublicWebProviderPolicyTopic:
    """One contractual/policy question using Sprint 31 states only."""

    topic: str
    state: CapabilityPolicyState
    evidence_source: str
    notes: str

    def __post_init__(self) -> None:
        if self.state not in {"allowed", "restricted", "prohibited", "unknown"}:
            raise ValueError("policy state is unknown and fails closed")
        if self.state == "allowed" and "ambiguous" in self.notes.casefold():
            raise ValueError("ambiguous terms must not be converted into allowed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "state": self.state,
            "evidence_source": self.evidence_source,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PublicWebProviderPolicyAudit:
    """Published-terms snapshot for one retrieval/search vendor."""

    provider_key: str
    display_name: str
    official_docs: tuple[str, ...]
    review_date: date
    completeness: str
    topics: tuple[PublicWebProviderPolicyTopic, ...]
    pricing_public_facts: str
    localization_notes: str
    freshness_notes: str
    structured_content_notes: str
    recommended_as_first_live_candidate: bool
    notes: str

    def __post_init__(self) -> None:
        if self.completeness not in {"incomplete", "recorded"}:
            raise ValueError("policy audit completeness is unknown and fails closed")
        if self.completeness == "recorded":
            raise ValueError(
                "public-web policy audits remain incomplete until owner credentials "
                "and a trusted legal/product review exist"
            )

    @property
    def grants_certification(self) -> bool:
        return False

    def topic_state(self, topic: str) -> CapabilityPolicyState:
        for item in self.topics:
            if item.topic == topic:
                return item.state
        return "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "display_name": self.display_name,
            "official_docs": list(self.official_docs),
            "review_date": self.review_date.isoformat(),
            "completeness": self.completeness,
            "topics": [item.to_dict() for item in self.topics],
            "pricing_public_facts": self.pricing_public_facts,
            "localization_notes": self.localization_notes,
            "freshness_notes": self.freshness_notes,
            "structured_content_notes": self.structured_content_notes,
            "recommended_as_first_live_candidate": self.recommended_as_first_live_candidate,
            "grants_certification": False,
            "notes": self.notes,
        }


def _topic(
    topic: str,
    state: CapabilityPolicyState,
    evidence_source: str,
    notes: str,
) -> PublicWebProviderPolicyTopic:
    return PublicWebProviderPolicyTopic(
        topic=topic,
        state=state,
        evidence_source=evidence_source,
        notes=notes,
    )


def brave_search_policy_audit() -> PublicWebProviderPolicyAudit:
    tos = "https://api-dashboard.search.brave.com/documentation/resources/terms-of-service"
    product = "https://brave.com/search/api/"
    query_docs = "https://api-dashboard.search.brave.com/app/documentation/web-search/query"
    llm_context = "https://api-dashboard.search.brave.com/api-reference/ai/llm_context/get"
    pricing = "https://api-dashboard.search.brave.com/documentation/pricing"
    return PublicWebProviderPolicyAudit(
        provider_key="brave_search",
        display_name="Brave Search API",
        official_docs=(tos, product, query_docs, pricing, llm_context),
        review_date=POLICY_REVIEW_DATE,
        completeness="incomplete",
        topics=(
            _topic(
                "api_use",
                "allowed",
                tos,
                "Published Terms grant a limited license to use the API and Search "
                "Results with Customer Applications. Not a PiqSavi production certification.",
            ),
            _topic(
                "search_result_reuse",
                "restricted",
                tos,
                "Use with Customer Applications is licensed; redistribution, resale, "
                "sublicensing, and creating a database of Search Results are prohibited "
                "except transient operational storage.",
            ),
            _topic(
                "url_result_display",
                "allowed",
                tos,
                "License includes using Search Results with Customer Applications. "
                "Third-party webpage content remains subject to the page publisher.",
            ),
            _topic(
                "caching",
                "restricted",
                f"{tos}; {product}",
                "Storing/caching/creating a database of Search Results is prohibited "
                "other than transient storage required for operation. Brave states "
                "storage/AI-training rights require a plan that explicitly grants them.",
            ),
            _topic(
                "content_retrieval",
                "unknown",
                f"{product}; {query_docs}",
                "Web Search returns URLs and snippets. Brave states it does not grant "
                "rights to third-party webpage content. Extra snippets are still snippets. "
                "No official page-fetch/extract endpoint is established as authorized "
                "PiqSavi offer evidence.",
            ),
            _topic(
                "attribution",
                "restricted",
                tos,
                "Attribution is optional. If used it must be conspicuous “POWERED BY "
                "BRAVE” plus logo, or other Brave-approved content. No partnership claim.",
            ),
            _topic(
                "rate_limits",
                "unknown",
                pricing,
                "Plan/credit based. Exact production rate limits are not established "
                "without an account/plan. Circumventing limits is prohibited.",
            ),
            _topic(
                "retention",
                "restricted",
                tos,
                "After termination, further use/retention of Search Results is prohibited. "
                "Transient operational storage only during the term.",
            ),
            _topic(
                "model_training_evaluation_improvement",
                "prohibited",
                tos,
                "Search API Terms dated 2026-09-01 prohibit using Search Results to "
                "create, evaluate, train, re-train, fine-tune, benchmark, or otherwise "
                "improve artificial intelligence models or services. This prohibition "
                "is not a blanket ban on all runtime LLM use.",
            ),
            _topic(
                "runtime_ai_llm_grounding_or_inference",
                "unknown",
                f"{tos}; {product}",
                "Brave publicly documents an LLM Context API for AI agents, LLM "
                "grounding, and RAG pipelines. The Search API Terms license use of "
                "Search Results with Customer Applications, but also restrict "
                "derivative works of Search Results. The reviewed Search API terms "
                "do not clearly establish that PiqSavi may transform, summarize, "
                "score, or send third-party Search Results through its runtime AI "
                "pipeline. URL-only discovery is different from using snippets as "
                "recommendation evidence. Third-Party Content and page-publisher "
                "rights remain separate. Ambiguity stays unknown, not allowed.",
            ),
            _topic(
                "country_localization",
                "unknown",
                query_docs,
                "Web Search documents a 2-character country parameter and "
                "x-loc-country as ISO 3166-1 alpha-2. PH is not in the visible "
                "published enum (AR/AU/AT plus examples US/DE and “+35 more”). "
                "PH localization via `country` remains unverified. Do not send "
                "`country=PH`. Do not substitute `x-loc-country` as a silent "
                "geographic stand-in. Preserve PH intent in the query text.",
            ),
            _topic(
                "freshness_metadata",
                "restricted",
                query_docs,
                "Freshness filter (pd/pw/pm/py/custom range) is documented as a query "
                "parameter based on reported page dates. That is index-age filtering, "
                "not current merchant offer evidence.",
            ),
            _topic(
                "structured_offer_fields",
                "unknown",
                query_docs,
                "Structured web results include title/url/description and optional "
                "extra_snippets. No documented canonical PHP listing-price field.",
            ),
            _topic(
                "product_discovery",
                "restricted",
                tos,
                "API use for Customer Applications is licensed. Production shopping "
                "discovery still requires credentials, PH relevance evidence, and "
                "trusted certification. Not certified.",
            ),
            _topic(
                "current_pricing",
                "unknown",
                f"{tos}; {product}",
                "Snippets are not canonical prices. Third-party page rights are not "
                "granted by Brave. Current pricing remains unknown/not certified.",
            ),
        ),
        pricing_public_facts=(
            "Published Search pricing observed 2026-09-18: prepaid Search at "
            "$5.00 per 1,000 requests. Product page still describes a free plan "
            "that requires a credit card as anti-fraud (card not charged for free "
            "plans) and states storage/AI-training needs a plan that grants those "
            "rights. Historical marketing still mentions 2,000 free queries/month. "
            "No paid signup was made. Exact current free-tier quota is account-dependent."
        ),
        localization_notes=(
            "Web Search documents a 2-character `country` parameter. Public docs "
            "show examples US/DE/AR/AU/AT and a truncated enum (“+35 more”). PH is "
            "not in the visible published list, so PH country targeting remains "
            "unverified. The live harness therefore omits `country` and keeps PH "
            "intent in the query text. Do not send `country=PH` until the published "
            "enum is recorded. `x-loc-country` is a client-location header, not a "
            "silent substitute for `country`."
        ),
        freshness_notes=(
            "Query freshness filter is documented. Result objects may include age "
            "metadata in live responses; not verified without credentials."
        ),
        structured_content_notes=(
            "URLs + snippets (+ extra_snippets). No official extract/contents API "
            "for full product pages. Brave explicitly does not grant third-party "
            "page rights."
        ),
        recommended_as_first_live_candidate=True,
        notes=(
            "Strongest documented license to use search results in a customer "
            "application, with a hard prohibition on using Search Results to "
            "create/evaluate/train/improve AI models. Runtime LLM grounding is "
            "not automatically prohibited and remains unknown. First live "
            "benchmark candidate if the owner supplies a key. URL discovery is "
            "not offer evidence. Not certified. Engineering interpretation is "
            "not counsel approval."
        ),
    )


def tavily_search_policy_audit() -> PublicWebProviderPolicyAudit:
    terms = "https://www.tavily.com/terms"
    search_docs = "https://docs.tavily.com/documentation/api-reference/endpoint/search"
    extract_docs = "https://docs.tavily.com/documentation/api-reference/endpoint/extract"
    credits = "https://docs.tavily.com/documentation/api-credits"
    about = "https://docs.tavily.com/documentation/about"
    return PublicWebProviderPolicyAudit(
        provider_key="tavily_search",
        display_name="Tavily Search API",
        official_docs=(terms, search_docs, extract_docs, credits, about),
        review_date=POLICY_REVIEW_DATE,
        completeness="incomplete",
        topics=(
            _topic(
                "api_use",
                "restricted",
                terms,
                "Terms grant a non-exclusive, revocable, non-transferable, "
                "non-sublicensable right to use Tavily APIs solely for Customer’s "
                "internal business purposes and according to documentation. "
                "Shopper-facing PiqSavi use is not clearly the same as internal "
                "business use. Do not convert that into allowed.",
            ),
            _topic(
                "search_result_reuse",
                "unknown",
                terms,
                "Published terms do not clearly grant unrestricted public display "
                "or comparison reuse of retrieved third-party content.",
            ),
            _topic(
                "url_result_display",
                "unknown",
                f"{terms}; {search_docs}",
                "Search responses include URLs. Display/redistribution rights for "
                "those URLs and snippets in a consumer shopping UI are not clearly "
                "stated as allowed.",
            ),
            _topic(
                "caching",
                "unknown",
                terms,
                "No explicit customer-side caching license comparable to Brave’s "
                "transient-storage clause was located. Tavily may cache operationally. "
                "Customer retention remains unknown.",
            ),
            _topic(
                "content_retrieval",
                "unknown",
                extract_docs,
                "Tavily Extract retrieves page content from specified URLs, including "
                "JS-rendered pages. That is Tavily’s service, not a PiqSavi crawler. "
                "Whether PiqSavi may use extracted merchant pages as offer evidence "
                "is a separate rights question (Tavily terms + page publisher). "
                "Unknown. Do not scrape merchants as a workaround.",
            ),
            _topic(
                "attribution",
                "unknown",
                terms,
                "No mandatory public attribution string comparable to Brave’s "
                "POWERED BY BRAVE clause was located in the reviewed terms excerpt.",
            ),
            _topic(
                "rate_limits",
                "restricted",
                f"{terms}; {credits}",
                "Credit/plan limits apply. Free Researcher plan is 1,000 credits/month. "
                "Exceeding documented usage is not allowed.",
            ),
            _topic(
                "retention",
                "unknown",
                terms,
                "Public terms reviewed do not establish a clear customer retention "
                "rule for search/extract outputs.",
            ),
            _topic(
                "model_training_evaluation_improvement",
                "unknown",
                f"{about}; {terms}",
                "Tavily product docs market LLM/RAG use. A Brave-style prohibition on "
                "using retrieved results to train, evaluate, or improve models was "
                "not located in the reviewed terms excerpt. Ambiguity stays unknown.",
            ),
            _topic(
                "runtime_ai_llm_grounding_or_inference",
                "unknown",
                f"{about}; {terms}",
                "Product documentation markets Tavily for LLM/RAG agents. That is "
                "not the same as permission to ingest merchant page content into "
                "PiqSavi scoring or shopper-facing AI summaries. Ambiguity stays unknown.",
            ),
            _topic(
                "country_localization",
                "unknown",
                search_docs,
                "Search `country` enum includes `philippines` for topic=general "
                "country boosting. That is documented technical targeting, not "
                "contractual authorization that PiqSavi may use Tavily as a PH "
                "shopping-data path.",
            ),
            _topic(
                "freshness_metadata",
                "unknown",
                search_docs,
                "Documentation describes real-time/customizable search. A durable "
                "per-result fetch timestamp / page-age contract was not established "
                "from the reviewed public schema excerpt.",
            ),
            _topic(
                "structured_offer_fields",
                "unknown",
                search_docs,
                "Results include URL, title, and content snippets/chunks. No "
                "documented canonical merchant offer schema with PHP listing price.",
            ),
            _topic(
                "product_discovery",
                "unknown",
                f"{terms}; {search_docs}",
                "Technically capable of returning PH-boosted URLs. Contractual "
                "permission for PiqSavi consumer discovery is not clearly allowed.",
            ),
            _topic(
                "current_pricing",
                "unknown",
                extract_docs,
                "Extracted page text is not automatically canonical current pricing. "
                "Snippet/extract prices stay discovery-only unless a later certified "
                "Level A/B path exists.",
            ),
        ),
        pricing_public_facts=(
            "Published 2026-09-18: Researcher free plan 1,000 credits/month, no "
            "credit card required. Basic/fast/ultra-fast search = 1 credit; "
            "advanced search = 2 credits. Extract basic = 1 credit per 5 successful "
            "URLs; advanced = 2 credits per 5. Pay-as-you-go $0.008/credit. No paid "
            "signup was made."
        ),
        localization_notes=(
            "Explicit `philippines` country boost when topic is general. "
            "include_domains/exclude_domains are documented."
        ),
        freshness_notes=(
            "Marketed as real-time. Per-result freshness evidence for current "
            "merchant offers is not established from public docs alone."
        ),
        structured_content_notes=(
            "Search snippets/chunks plus optional Extract raw page content. "
            "Extract is a vendor retrieval path, not PiqSavi scraping, and is "
            "still not certified offer evidence."
        ),
        recommended_as_first_live_candidate=True,
        notes=(
            "Useful comparison and possible Level B retrieval *if* later policy "
            "review allows Extract. Internal-business-purpose wording keeps "
            "shopper-facing reuse unknown. Not certified."
        ),
    )


def exa_search_policy_audit() -> PublicWebProviderPolicyAudit:
    terms = "https://exa.ai/assets/Exa_Labs_Terms_of_Service.pdf"
    contents = "https://exa.ai/docs/reference/get-contents"
    pricing = "https://exa.ai/docs/reference/pricing"
    return PublicWebProviderPolicyAudit(
        provider_key="exa_search",
        display_name="Exa Search API",
        official_docs=(terms, contents, pricing),
        review_date=POLICY_REVIEW_DATE,
        completeness="incomplete",
        topics=(
            _topic(
                "api_use",
                "restricted",
                terms,
                "Terms grant a revocable, non-transferable, non-sublicensable right "
                "to use APIs for limited purposes in the documentation. Not a "
                "shopping-data certification.",
            ),
            _topic(
                "search_result_reuse",
                "unknown",
                terms,
                "Website/API terms restrict copying, distributing, or offering for "
                "sale information obtained through the Services except as expressly "
                "permitted. Shopper-facing reuse is not clearly allowed.",
            ),
            _topic(
                "url_result_display",
                "unknown",
                terms,
                "Display of retrieved URLs in a consumer product is not clearly "
                "permitted beyond documentation-limited API use.",
            ),
            _topic(
                "caching",
                "unknown",
                f"{terms}; {contents}",
                "Exa documents its own content cache / livecrawl controls "
                "(maxAgeHours). Customer-side caching rights are not clearly granted.",
            ),
            _topic(
                "content_retrieval",
                "unknown",
                contents,
                "Contents API can return page text/highlights/summaries and can "
                "livecrawl. That is Exa’s retrieval, not a PiqSavi crawler. "
                "Permission to treat retrieved merchant pages as PiqSavi offer "
                "evidence remains unknown.",
            ),
            _topic(
                "attribution",
                "unknown",
                terms,
                "No mandatory consumer attribution string was located in the "
                "reviewed terms excerpt.",
            ),
            _topic(
                "rate_limits",
                "restricted",
                f"{terms}; {pricing}",
                "Usage must comply with documented call-volume limits. Pay-as-you-go "
                "billing is documented.",
            ),
            _topic(
                "retention",
                "unknown",
                terms,
                "Customer retention of retrieved contents is not clearly licensed. "
                "Exa terms grant Exa a broad license to user input/output to provide "
                "and improve services.",
            ),
            _topic(
                "model_training_evaluation_improvement",
                "unknown",
                terms,
                "Exa is marketed for AI search. A Brave-style prohibition on using "
                "retrieved information to train, evaluate, or improve models was not "
                "located in the reviewed terms excerpt. Ambiguity stays unknown.",
            ),
            _topic(
                "runtime_ai_llm_grounding_or_inference",
                "unknown",
                terms,
                "Product is marketed for AI search. Terms still restrict copying/"
                "distribution of obtained information. Whether PiqSavi may send Exa "
                "results through its runtime AI pipeline is not clearly established. "
                "Ambiguity stays unknown.",
            ),
            _topic(
                "country_localization",
                "unknown",
                contents,
                "No documented PH/country targeting parameter comparable to Tavily’s "
                "philippines enum or Brave’s country filter was established from "
                "the reviewed Contents/Search docs.",
            ),
            _topic(
                "freshness_metadata",
                "restricted",
                contents,
                "maxAgeHours is documented (0 = livecrawl, -1 = cache-only, omit = "
                "cache then livecrawl fallback). Useful technical freshness control; "
                "not by itself current merchant-offer certification.",
            ),
            _topic(
                "structured_offer_fields",
                "unknown",
                contents,
                "Text/highlights/summaries are page content views, not a canonical "
                "PHP offer schema.",
            ),
            _topic(
                "product_discovery",
                "unknown",
                terms,
                "Search can return URLs. PH shopping usefulness and contractual "
                "permission are unverified.",
            ),
            _topic(
                "current_pricing",
                "unknown",
                contents,
                "Livecrawled page text is still not automatic canonical pricing. "
                "Unknown / not certified.",
            ),
        ),
        pricing_public_facts=(
            "Published 2026-09-18: pay-as-you-go, no subscription. New accounts "
            "get $20 free credits; free tier adds $10/month. Search $7 / 1k "
            "requests (up to 10 results). Contents $1 / 1k pages per content type. "
            "Summaries $1 / 1k pages. No paid signup was made."
        ),
        localization_notes=(
            "No verified PH country parameter from reviewed public docs. "
            "Comparison-only unless live results prove PH retailer coverage."
        ),
        freshness_notes=(
            "Documented livecrawl vs cache via maxAgeHours. Stronger technical "
            "freshness control than snippet search, still not certified offers."
        ),
        structured_content_notes=(
            "Search plus Contents text/highlights/summary. Materially useful as a "
            "Level B comparison if policy later permits. Not the first license-clear "
            "candidate."
        ),
        recommended_as_first_live_candidate=False,
        notes=(
            "Comparison candidate for provider-fetched page content. Terms are "
            "more restrictive/ambiguous for consumer reuse than Brave’s Customer "
            "Applications license. Not certified. Not required for first live test."
        ),
    )


def public_web_provider_policy_audits() -> tuple[PublicWebProviderPolicyAudit, ...]:
    return (
        brave_search_policy_audit(),
        tavily_search_policy_audit(),
        exa_search_policy_audit(),
    )


def first_live_benchmark_candidates() -> tuple[str, ...]:
    return tuple(
        item.provider_key
        for item in public_web_provider_policy_audits()
        if item.recommended_as_first_live_candidate
    )
