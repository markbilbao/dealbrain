"""Lazada marketplace connector — mocked data only (no scraping / APIs)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.intelligence.marketplace.lazada.mock_data import LAZADA_MOCK_LISTINGS


class LazadaConnector(MarketplaceConnector):
    """Mock Lazada adapter returning canned listings."""

    @property
    def marketplace_name(self) -> str:
        return "lazada"

    def search(self, query: str) -> list[MarketplaceListing]:
        needle = query.strip().lower()
        if not needle:
            return []
        matches: list[MarketplaceListing] = []
        for raw in LAZADA_MOCK_LISTINGS:
            listing = self.normalize_listing(raw)
            haystack = f"{listing.title} {listing.seller}".lower()
            if needle in haystack:
                matches.append(listing)
        return matches

    def get_product(self, product_id: str) -> MarketplaceListing | None:
        for raw in LAZADA_MOCK_LISTINGS:
            if str(raw.get("itemId", "")) == product_id:
                return self.normalize_listing(raw)
        return None

    def normalize_listing(self, raw: Mapping[str, Any]) -> MarketplaceListing:
        rating_raw = raw.get("ratingScore")
        rating = float(rating_raw) if rating_raw is not None else None
        stock_str = str(raw.get("availability", "in stock")).lower()
        if "out" in stock_str:
            availability = AvailabilityStatus.OUT_OF_STOCK
        elif "limited" in stock_str or "low" in stock_str:
            availability = AvailabilityStatus.LIMITED
        elif "in stock" in stock_str or stock_str == "instock":
            availability = AvailabilityStatus.IN_STOCK
        else:
            availability = AvailabilityStatus.UNKNOWN

        item_id = str(raw.get("itemId", ""))
        return MarketplaceListing(
            marketplace=self.marketplace_name,
            product_id=item_id,
            title=str(raw.get("name", "")),
            price=float(raw.get("price", 0)),
            currency=str(raw.get("currency", "PHP")),
            seller=str(raw.get("sellerName", "")),
            rating=rating,
            url=str(raw.get("productUrl", f"https://www.lazada.com.ph/products/i{item_id}.html")),
            availability=availability,
        )

    def get_price(self, product_id: str) -> float | None:
        listing = self.get_product(product_id)
        return None if listing is None else listing.price

    def get_availability(self, product_id: str) -> AvailabilityStatus:
        listing = self.get_product(product_id)
        if listing is None:
            return AvailabilityStatus.UNKNOWN
        return listing.availability
