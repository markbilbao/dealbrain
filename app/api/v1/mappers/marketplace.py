"""Map Marketplace Intelligence domain results to HTTP response schemas."""

from __future__ import annotations

from app.domain.entities.marketplace_listing import MarketplaceListing, MarketplaceSearchResult
from app.schemas.marketplace import MarketplaceListingPayload, MarketplaceSearchResponse


def to_search_response(result: MarketplaceSearchResult) -> MarketplaceSearchResponse:
    """Convert an aggregated search result into the public response schema."""
    return MarketplaceSearchResponse(
        query=result.query,
        results=[_to_listing_payload(listing) for listing in result.results],
    )


def _to_listing_payload(listing: MarketplaceListing) -> MarketplaceListingPayload:
    return MarketplaceListingPayload(
        marketplace=listing.marketplace,
        title=listing.title,
        price=listing.price,
        currency=listing.currency,
        seller=listing.seller,
        rating=listing.rating,
        url=listing.url,
    )
