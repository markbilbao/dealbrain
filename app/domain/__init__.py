"""Domain layer — business entities, value objects, and port interfaces.

Framework-independent. Product Identity V1.0 lives here as contracts and VOs;
deterministic implementations live under ``app.intelligence``.
"""

from app.domain.entities.canonical_product import CanonicalProduct, ParseSignal
from app.domain.entities.product_match import FieldConflict, MatchType, ProductMatchResult
from app.domain.entities.product_relation import (
    ProductRelation,
    ProductRelationType,
    RelationDirection,
)
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    ParseListingResult,
    RegisteredCanonicalProduct,
    RegistryResolveResult,
)
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher

__all__ = [
    "CanonicalProduct",
    "CanonicalProductRegistry",
    "CanonicalProductStatus",
    "CanonicalProductStore",
    "FieldConflict",
    "MatchType",
    "ParseListingResult",
    "ParseSignal",
    "ProductIntelligenceEngine",
    "ProductMatchResult",
    "ProductMatcher",
    "ProductRelation",
    "ProductRelationType",
    "RegisteredCanonicalProduct",
    "RegistryResolveResult",
    "RelationDirection",
]
