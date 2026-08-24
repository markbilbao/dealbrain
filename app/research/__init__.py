"""Sprint 31 research execution routing package.

Certified-provider catalog, capability derivation, and fail-closed planning.
Does not perform HTTP or live merchant research.
"""

from app.research.capabilities import derive_required_capabilities
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    ResearchProviderRegistry,
    production_research_provider_registry,
    research_provider_registry_for_tests,
)

__all__ = [
    "ResearchProviderRegistry",
    "StaticResearchProvider",
    "derive_required_capabilities",
    "production_research_provider_registry",
    "research_provider_registry_for_tests",
]
