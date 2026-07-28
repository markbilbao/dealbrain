"""Shopee marketplace connector — mocked data only (no scraping / APIs)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.intelligence.marketplace.shopee.mock_data import SHOPEE_MOCK_LISTINGS


class ShopeeConnector(MarketplaceConnector):
    """Mock Shopee adapter returning canned listings."""

    @property
    def marketplace_name(self) -> str:
        return "shopee"

    def search(self, query: str) -> list[MarketplaceListing]:
        needle = query.strip().lower()
        if not needle:
            return []
        matches: list[MarketplaceListing] = []
        for raw in SHOPEE_MOCK_LISTINGS:
            listing = self.normalize_listing(raw)
            haystack = f"{listing.title} {listing.seller}".lower()
            if needle in haystack:
                matches.append(listing)
        return matches

    def get_product(self, product_id: str) -> MarketplaceListing | None:
        for raw in SHOPEE_MOCK_LISTINGS:
            if str(raw.get("itemid", "")) == product_id:
                return self.normalize_listing(raw)
        return None

    def normalize_listing(self, raw: Mapping[str, Any]) -> MarketplaceListing:
        rating_raw = raw.get("rating_star")
        rating = float(rating_raw) if rating_raw is not None else None
        stock = int(raw.get("stock", 0) or 0)
        if stock <= 0:
            availability = AvailabilityStatus.OUT_OF_STOCK
        elif stock < 5:
            availability = AvailabilityStatus.LIMITED
        else:
            availability = AvailabilityStatus.IN_STOCK

        item_id = str(raw.get("itemid", ""))
        shop_id = str(raw.get("shopid", ""))
        return MarketplaceListing(
            marketplace=self.marketplace_name,
            product_id=item_id,
            title=str(raw.get("name", "")),
            price=float(raw.get("price", 0)) / 100_000,  # Shopee stores price * 100000
            currency=str(raw.get("currency", "PHP")),
            seller=str(raw.get("shop_name", "")),
            rating=rating,
            url=f"https://shopee.ph/product/{shop_id}/{item_id}",
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
