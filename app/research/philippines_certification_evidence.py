"""Documentary Philippines merchant certification evidence — Sprint 32.3.

Static snapshots of what official repository evidence can prove today.
Not loaded by production runtime factories. Not certifications.
"""

from __future__ import annotations

from datetime import date

from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderCertificationEvidence,
)
from app.research.certification_evidence import (
    ResearchProviderCertificationEvidenceCatalog,
    make_research_provider_certification_evidence,
)

COUNSEL_CLEARANCE_DATE = date(2026, 8, 25)
PHILIPPINES_MARKET = "PH"

_AUTHORITATIVE_SOURCES = (
    "docs/roadmap/evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md"
    "; docs/roadmap/evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md"
    "; docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md"
    "; docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md"
)

_SHARED_RESTRICTIONS = (
    "application clearance only",
    "merchant approval not established",
    "API/data permission unknown",
    "production use not established",
)

_MERCHANT_DATA_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
)

_MERCHANTS: tuple[tuple[str, str, str, str], ...] = (
    (
        "ph-shopee",
        "shopee",
        "Shopee merchant/program application counsel-cleared 2026-08-25. "
        "Shopee Affiliate Program is separate from Shopee Seller/ISV Open Platform.",
        "Counsel-cleared to apply. Application not submitted on official main. "
        "Public merchant documentation is not a PiqSavi access grant. "
        "Affiliate permission unknown. Product-data/API rights unknown. "
        "Credentials absent. No production Sprint 31 provider descriptor. "
        "Sprint 26 owns application; Sprint 32 owns PH certification.",
    ),
    (
        "ph-lazada",
        "lazada",
        "Lazada merchant/program application counsel-cleared 2026-08-25. "
        "Lazada Affiliate Program is separate from Lazada Open Platform.",
        "Counsel-cleared to apply. Application not submitted on official main. "
        "Technical mocks/stubs are placeholders only. "
        "Affiliate permission unknown. Product-data/API rights unknown. "
        "Credentials absent. No production Sprint 31 provider descriptor. "
        "Sprint 26 owns application; Sprint 32 owns PH certification.",
    ),
    (
        "ph-tiktok-shop",
        "tiktok_shop",
        "TikTok Shop merchant/program application counsel-cleared 2026-08-25. "
        "Creator affiliate, Partner Center, and developer API are separate programs.",
        "Counsel-cleared to apply. Application not submitted on official main. "
        "Demo affiliate placeholder targets US/GB/SG, not PH. "
        "No confirmed PH research provider. Affiliate permission unknown. "
        "Product-data/API rights unknown. Credentials absent. "
        "Sprint 26 owns application; Sprint 32 owns PH certification.",
    ),
    (
        "ph-amazon",
        "amazon",
        "Amazon merchant/program application counsel-cleared 2026-08-25. "
        "Amazon Associates is separate from Creators API and from PA-API / SP-API.",
        "Counsel-cleared to apply. Application not submitted on official main. "
        "Demo affiliate placeholder targets US, not PH. "
        "Affiliate permission unknown. Product-data/API rights unknown. "
        "Credentials absent. No production Sprint 31 provider descriptor. "
        "Sprint 26 owns application; Sprint 32 owns PH certification.",
    ),
    (
        "ph-temu",
        "temu",
        "Temu merchant/program application counsel-cleared 2026-08-25. "
        "Affiliate, Influencer, and Media Publisher tracks are separate from any partner API.",
        "Counsel-cleared to apply. Application not submitted on official main. "
        "No technical provider path in the repository. "
        "Affiliate permission unknown. Product-data/API rights unknown. "
        "Credentials absent. No production Sprint 31 provider descriptor. "
        "Sprint 26 owns application; Sprint 32 owns PH certification.",
    ),
)


def philippines_merchant_certification_evidence_records() -> tuple[
    ResearchProviderCertificationEvidence, ...
]:
    """Exact PH merchant-data evidence snapshots. Not production runtime state."""

    records: list[ResearchProviderCertificationEvidence] = []
    for provider_id, source, program_reference, notes in _MERCHANTS:
        for capability in _MERCHANT_DATA_CAPABILITIES:
            records.append(
                make_research_provider_certification_evidence(
                    provider_id=provider_id,
                    capability=capability,
                    market=PHILIPPINES_MARKET,
                    source=source,
                    evidence_source=_AUTHORITATIVE_SOURCES,
                    evidence_date=COUNSEL_CLEARANCE_DATE,
                    program_reference=program_reference,
                    restrictions=_SHARED_RESTRICTIONS,
                    completeness="incomplete",
                    notes=notes,
                    test_fixture=False,
                )
            )
    return tuple(records)


def philippines_merchant_certification_evidence_catalog() -> (
    ResearchProviderCertificationEvidenceCatalog
):
    """Explicit documentary catalog. Not the production runtime factory."""

    return ResearchProviderCertificationEvidenceCatalog(
        philippines_merchant_certification_evidence_records(),
        allow_test_evidence=False,
    )


def philippines_merchant_provider_ids() -> tuple[str, ...]:
    return tuple(provider_id for provider_id, _source, _program, _notes in _MERCHANTS)
