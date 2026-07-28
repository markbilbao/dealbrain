"""Product Intelligence application service.

Orchestrates parser, canonical registry, and product matcher through domain
ports only. Returns domain value objects — HTTP schema mapping lives in the
API layer.
"""

from __future__ import annotations

from app.domain.entities.product_match import ProductMatchResult
from app.domain.entities.registered_product import ParseListingResult
from app.domain.exceptions import InsufficientCanonicalIdentityError, UnsupportedProductError
from app.domain.interfaces.canonical_registry import CanonicalProductRegistry
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher


class ProductIntelligenceService:
    """Use-case orchestration for listing → parse → registry / match."""

    def __init__(
        self,
        parser: ProductIntelligenceEngine,
        registry: CanonicalProductRegistry,
        matcher: ProductMatcher,
    ) -> None:
        self._parser = parser
        self._registry = registry
        self._matcher = matcher

    async def parse_listing(self, title: str) -> ParseListingResult:
        """Parse a messy title and resolve it to a canonical registry identity."""
        cleaned = title.strip()
        if not cleaned:
            raise UnsupportedProductError(title, "title must not be blank")

        parsed = self._parser.parse(cleaned)

        try:
            resolved = await self._registry.resolve(parsed)
        except InsufficientCanonicalIdentityError as exc:
            fields = ", ".join(exc.missing_fields)
            raise UnsupportedProductError(
                cleaned,
                f"Unsupported product listing: could not determine {fields}",
            ) from exc

        return ParseListingResult(
            original_title=cleaned,
            product=resolved.product,
            confidence=parsed.confidence,
            is_new_product=resolved.created,
            signals=parsed.signals,
        )

    def match_listings(self, title_a: str, title_b: str) -> ProductMatchResult:
        """Parse two listing titles, then compare via the Product Matcher port."""
        cleaned_a = title_a.strip()
        cleaned_b = title_b.strip()
        if not cleaned_a or not cleaned_b:
            raise UnsupportedProductError(
                title_a if not cleaned_a else title_b,
                "title must not be blank",
            )

        product_a = self._parser.parse(cleaned_a)
        product_b = self._parser.parse(cleaned_b)
        return self._matcher.match_products(product_a, product_b)
