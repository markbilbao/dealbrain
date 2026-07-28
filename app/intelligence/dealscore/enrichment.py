"""Supplemental deal attributes for mocked marketplace listings.

Marketplace connectors remain untouched. DealScore enriches known mock
listings with shipping, official-store, warranty, and return-policy data so
total purchase cost and component scores are demonstrable and testable.
"""

from __future__ import annotations

from app.domain.entities.deal_score import DealListingAttributes, ScoreableListing
from app.domain.entities.marketplace_listing import MarketplaceListing

# Keyed by (marketplace, product_id). Values intentionally vary so demos and
# tests can exercise free vs paid shipping, official stores, and missing fields.
MOCK_DEAL_ATTRIBUTES: dict[tuple[str, str], DealListingAttributes] = {
    ("shopee", "1001001"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=7,
    ),
    ("shopee", "1001002"): DealListingAttributes(
        shipping_cost=150.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=7,
    ),
    ("shopee", "1001003"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=False,
        warranty_months=6,
        return_policy_days=7,
    ),
    ("shopee", "1001004"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    ),
    ("shopee", "1001005"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=7,
    ),
    ("lazada", "2002001"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    ),
    ("lazada", "2002002"): DealListingAttributes(
        shipping_cost=99.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=7,
    ),
    ("lazada", "2002003"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=False,
        warranty_months=6,
        return_policy_days=7,
    ),
    ("lazada", "2002004"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    ),
    ("lazada", "2002005"): DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    ),
}

_OFFICIAL_HINTS = (
    "official",
    "authorized",
    "flagship",
    "lazmall",
    "apple store",
)


def infer_official_store(seller: str) -> bool | None:
    """Heuristic official-store signal from seller name when enrichment is absent."""
    cleaned = seller.strip().lower()
    if not cleaned:
        return None
    return any(hint in cleaned for hint in _OFFICIAL_HINTS)


def resolve_deal_attributes(listing: MarketplaceListing) -> DealListingAttributes:
    """Resolve deal attributes for a listing without modifying connectors."""
    key = (listing.marketplace.lower(), listing.product_id)
    if key in MOCK_DEAL_ATTRIBUTES:
        return MOCK_DEAL_ATTRIBUTES[key]

    return DealListingAttributes(
        shipping_cost=0.0,
        is_official_store=infer_official_store(listing.seller),
        warranty_months=None,
        return_policy_days=None,
    )


def to_scoreable_listing(
    listing: MarketplaceListing,
    attributes: DealListingAttributes | None = None,
) -> ScoreableListing:
    """Build a ScoreableListing from a normalized marketplace listing."""
    attrs = attributes if attributes is not None else resolve_deal_attributes(listing)
    return ScoreableListing(
        listing_id=listing.product_id,
        marketplace=listing.marketplace,
        title=listing.title,
        price=listing.price,
        currency=listing.currency,
        seller=listing.seller,
        seller_rating=listing.rating,
        url=listing.url,
        availability=listing.availability,
        shipping_cost=attrs.shipping_cost,
        is_official_store=attrs.is_official_store,
        warranty_months=attrs.warranty_months,
        return_policy_days=attrs.return_policy_days,
        source_listing=listing,
    )
