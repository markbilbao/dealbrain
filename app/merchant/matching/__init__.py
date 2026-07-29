"""Product matching integration for merchant submissions — Sprint 18 matcher."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.marketplace_data import MatchAmbiguityStatus
from app.domain.entities.merchant import MerchantMatchResult
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher

# Re-export catalog entry for fixtures / services
__all__ = ["CatalogEntry", "MerchantProductMatcher"]


class MerchantProductMatcher:
    """Wrap Sprint 18 MarketplaceProductMatcher for merchant submissions.

    Never silently merges low-confidence matches — ambiguous results produce
    review records instead.
    """

    def __init__(self, catalog: Sequence[CatalogEntry] | None = None) -> None:
        self._matcher = MarketplaceProductMatcher(catalog)

    def register(self, entry: CatalogEntry) -> None:
        self._matcher.register(entry)

    def match(
        self,
        *,
        brand: str | None = None,
        model: str | None = None,
        title: str = "",
        sku: str | None = None,
        upc: str | None = None,
        ean: str | None = None,
        gtin: str | None = None,
        merchant_product_id: str | None = None,
    ) -> MerchantMatchResult:
        decision = self._matcher.match(
            brand=brand,
            model=model,
            title=title,
            sku=sku,
            upc=upc,
            ean=ean,
            gtin=gtin,
            marketplace_product_id=merchant_product_id,
        )
        review_required = decision.ambiguity in (
            MatchAmbiguityStatus.AMBIGUOUS,
            MatchAmbiguityStatus.CONFLICT,
        )
        # Never silently merge low-confidence / ambiguous matches.
        matched_id = decision.matched_product_id
        if review_required:
            matched_id = None
        return MerchantMatchResult(
            matched_product_id=matched_id,
            confidence=decision.confidence,
            reasons=decision.reasons,
            ambiguity=decision.ambiguity.value,
            candidate_ids=decision.candidate_ids,
            review_required=review_required or decision.ambiguity == MatchAmbiguityStatus.UNMATCHED,
        )
