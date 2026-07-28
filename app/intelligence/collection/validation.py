"""Listing validation helpers for marketplace collection.

Malformed listings are rejected before Price History persistence.
"""

from __future__ import annotations

from app.domain.entities.marketplace_listing import MarketplaceListing

REQUIRED_LISTING_FIELDS = ("marketplace", "product_id", "title", "currency")


def validate_listing(listing: MarketplaceListing) -> list[str]:
    """Return validation error messages; empty list means the listing is valid."""
    errors: list[str] = []
    if not listing.marketplace or not str(listing.marketplace).strip():
        errors.append("marketplace is required")
    if not listing.product_id or not str(listing.product_id).strip():
        errors.append("product_id is required")
    if not listing.title or not str(listing.title).strip():
        errors.append("title is required")
    if not listing.currency or not str(listing.currency).strip():
        errors.append("currency is required")
    try:
        price = float(listing.price)
    except (TypeError, ValueError):
        errors.append("price must be numeric")
        return errors
    if price < 0:
        errors.append("price must be non-negative")
    return errors


def is_valid_listing(listing: MarketplaceListing) -> bool:
    return not validate_listing(listing)
