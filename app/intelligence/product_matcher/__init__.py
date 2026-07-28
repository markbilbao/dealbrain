"""Product Matching Engine — exact-variant comparison of parsed products.

Responsibility: decide whether two CanonicalProduct values refer to the same
sellable variant. Depends only on parser outputs; does not parse titles or
touch the registry.
"""

from app.intelligence.product_matcher.exact_variant import ExactVariantProductMatcher

__all__ = ["ExactVariantProductMatcher"]
