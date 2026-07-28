"""Domain entities and value objects for Product Identity."""

from app.domain.entities.canonical_product import CanonicalProduct, ParseSignal
from app.domain.entities.product_match import (
    FieldCompareStatus,
    FieldConflict,
    MatchType,
    ProductMatchResult,
)
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

__all__ = [
    "CanonicalProduct",
    "CanonicalProductStatus",
    "FieldCompareStatus",
    "FieldConflict",
    "MatchType",
    "ParseListingResult",
    "ParseSignal",
    "ProductMatchResult",
    "ProductRelation",
    "ProductRelationType",
    "RegisteredCanonicalProduct",
    "RegistryResolveResult",
    "RelationDirection",
]
