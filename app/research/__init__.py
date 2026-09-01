"""Sprint 31 research execution routing package.

Certified-provider catalog, capability derivation, and fail-closed planning.
Does not perform HTTP or live merchant research.
"""

from app.research.capabilities import derive_required_capabilities
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.certification_evidence import (
    ResearchProviderCertificationEvidenceCatalog,
    production_research_provider_certification_evidence_catalog,
    research_provider_certification_evidence_catalog_for_tests,
)
from app.research.philippines_certification_evidence import (
    philippines_merchant_certification_evidence_catalog,
    philippines_merchant_certification_evidence_records,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    ResearchProviderRegistry,
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    production_research_provider_routing_policy_catalog,
    research_provider_routing_policy_catalog_for_tests,
)

__all__ = [
    "ResearchProviderCertificationCatalog",
    "ResearchProviderCertificationEvidenceCatalog",
    "ResearchProviderRegistry",
    "ResearchProviderRoutingPolicyCatalog",
    "StaticResearchProvider",
    "derive_required_capabilities",
    "production_research_provider_certification_catalog",
    "production_research_provider_certification_evidence_catalog",
    "production_research_provider_registry",
    "philippines_merchant_certification_evidence_catalog",
    "philippines_merchant_certification_evidence_records",
    "production_research_provider_routing_policy_catalog",
    "research_provider_certification_catalog_for_tests",
    "research_provider_certification_evidence_catalog_for_tests",
    "research_provider_registry_for_tests",
    "research_provider_routing_policy_catalog_for_tests",
]
