"""DealBrain intelligence modules — Product Identity V1.

Deterministic algorithms live here. Implementations are replaceable via
domain ports under ``app.domain.interfaces``.

Product Identity V1.0 comprises:
- Product Intelligence Engine (parser)
- Canonical Product Registry
- Product Matching Engine
"""

from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
    build_identity_key,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser

__all__ = [
    "CanonicalProductRegistryService",
    "ExactVariantProductMatcher",
    "InMemoryCanonicalProductStore",
    "RuleBasedProductParser",
    "build_identity_key",
]

# Frozen Product Identity layer version (parser + registry + matcher).
PRODUCT_IDENTITY_VERSION = "1.0.0"
