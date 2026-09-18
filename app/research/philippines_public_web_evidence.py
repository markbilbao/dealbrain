"""Documentary PH public-web discovery evidence — Sprint 32.

Candidate identities only. Not loaded by production runtime factories.
Not certifications. Search providers are not merchants.
"""

from __future__ import annotations

from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderCertificationEvidence,
)
from app.research.certification_evidence import (
    ResearchProviderCertificationEvidenceCatalog,
    make_research_provider_certification_evidence,
)
from app.research.public_web_policy import POLICY_REVIEW_DATE, public_web_provider_policy_audits

PHILIPPINES_MARKET = "PH"
PUBLIC_WEB_EVIDENCE_DATE = POLICY_REVIEW_DATE

_AUTHORITATIVE_SOURCES = (
    "docs/roadmap/evidence/SPRINT_32_PUBLIC_WEB_PROVIDER_EVALUATION.md"
    "; docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
    "; docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md"
)

_SHARED_RESTRICTIONS = (
    "search provider is not a merchant",
    "search snippet is not canonical price evidence",
    "credentials not issued",
    "live current-data response absent",
    "production use not established",
    "API/data permission unknown or restricted pending owner review",
)

_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    (
        "ph-brave-search",
        "Brave Search API. Limited Customer Applications license. Using Search "
        "Results to create/evaluate/train/improve AI models is prohibited. Runtime "
        "LLM grounding remains unknown, not a blanket AI ban. Storage restricted. "
        "Third-party webpage rights not granted. Not a merchant.",
        "Documentary public-web discovery candidate only. No owner credentials. "
        "No live PH shopping response. Snippets cannot become scored offers. "
        "Shopee/Lazada URLs if later returned are indexed URLs, not direct integrations.",
    ),
    (
        "ph-tavily-search",
        "Tavily Search API. Terms reviewed as internal business use; shopper-facing "
        "reuse unknown. Philippines country boost documented. Extract is not PiqSavi "
        "scraping and is not certified offer evidence. Not a merchant.",
        "Documentary public-web discovery candidate only. No owner credentials. "
        "No live PH shopping response. Snippets cannot become scored offers.",
    ),
    (
        "ph-exa-search",
        "Exa Search API comparison candidate. Contents/livecrawl may later support "
        "Level B analysis if policy permits. Consumer reuse unknown. Not a merchant.",
        "Documentary comparison candidate only. Not the first live-test requirement. "
        "No owner credentials. No live PH shopping response.",
    ),
)


def philippines_public_web_certification_evidence_records() -> tuple[
    ResearchProviderCertificationEvidence, ...
]:
    """Exact PH public-web discovery snapshots. Not production runtime state."""

    audits = {item.provider_key: item for item in public_web_provider_policy_audits()}
    mapping = {
        "ph-brave-search": "brave_search",
        "ph-tavily-search": "tavily_search",
        "ph-exa-search": "exa_search",
    }
    records: list[ResearchProviderCertificationEvidence] = []
    for provider_id, program_reference, notes in _CANDIDATES:
        audit = audits[mapping[provider_id]]
        records.append(
            make_research_provider_certification_evidence(
                provider_id=provider_id,
                capability=ResearchCapability.PRODUCT_DISCOVERY,
                market=PHILIPPINES_MARKET,
                source=None,
                source_scope="source_agnostic",
                evidence_source=_AUTHORITATIVE_SOURCES,
                evidence_date=PUBLIC_WEB_EVIDENCE_DATE,
                program_reference=program_reference,
                restrictions=_SHARED_RESTRICTIONS + (f"policy completeness={audit.completeness}",),
                completeness="incomplete",
                notes=notes,
                test_fixture=False,
            )
        )
    return tuple(records)


def philippines_public_web_certification_evidence_catalog() -> (
    ResearchProviderCertificationEvidenceCatalog
):
    """Explicit documentary catalog. Not the production runtime factory."""

    return ResearchProviderCertificationEvidenceCatalog(
        philippines_public_web_certification_evidence_records(),
        allow_test_evidence=False,
    )


def philippines_public_web_provider_ids() -> tuple[str, ...]:
    return tuple(provider_id for provider_id, _program, _notes in _CANDIDATES)
