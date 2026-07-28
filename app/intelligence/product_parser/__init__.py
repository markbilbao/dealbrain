"""Product Intelligence Engine — deterministic product-name parsing.

Responsibility: turn messy listing titles into immutable CanonicalProduct
value objects with explainability signals. Knows nothing about the registry,
matcher, or marketplaces.
"""

from app.intelligence.product_parser.engine import RuleBasedProductParser

__all__ = ["RuleBasedProductParser"]
