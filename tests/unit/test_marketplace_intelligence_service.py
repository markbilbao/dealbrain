"""Unit tests for Marketplace Intelligence service aggregation."""

from collections.abc import Mapping
from typing import Any

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.intelligence.marketplace.lazada import LazadaConnector
from app.intelligence.marketplace.shopee import ShopeeConnector
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService


class _StubConnector(MarketplaceConnector):
    def __init__(self, name: str, listings: list[MarketplaceListing]) -> None:
        self._name = name
        self._listings = listings

    @property
    def marketplace_name(self) -> str:
        return self._name

    def search(self, query: str) -> list[MarketplaceListing]:
        needle = query.lower()
        return [item for item in self._listings if needle in item.title.lower()]

    def get_product(self, product_id: str) -> MarketplaceListing | None:
        for item in self._listings:
            if item.product_id == product_id:
                return item
        return None

    def normalize_listing(self, raw: Mapping[str, Any]) -> MarketplaceListing:
        raise NotImplementedError

    def get_price(self, product_id: str) -> float | None:
        listing = self.get_product(product_id)
        return None if listing is None else listing.price

    def get_availability(self, product_id: str) -> AvailabilityStatus:
        listing = self.get_product(product_id)
        return AvailabilityStatus.UNKNOWN if listing is None else listing.availability


def test_service_aggregates_mock_connectors() -> None:
    service = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()],
    )
    result = service.search("iPhone 17 Pro Max")

    assert result.query == "iPhone 17 Pro Max"
    marketplaces = {item.marketplace for item in result.results}
    assert marketplaces == {"shopee", "lazada"}
    assert len(result.results) >= 2


def test_service_aggregates_stub_connectors_in_order() -> None:
    a = MarketplaceListing(
        marketplace="amazon",
        product_id="a1",
        title="Widget A",
        price=10.0,
        currency="USD",
        seller="A",
        rating=4.0,
        url="https://example.com/a1",
    )
    b = MarketplaceListing(
        marketplace="ebay",
        product_id="b1",
        title="Widget B",
        price=9.0,
        currency="USD",
        seller="B",
        rating=3.5,
        url="https://example.com/b1",
    )
    service = MarketplaceIntelligenceService(
        connectors=[
            _StubConnector("amazon", [a]),
            _StubConnector("ebay", [b]),
        ],
    )

    result = service.search("Widget")
    assert [item.marketplace for item in result.results] == ["amazon", "ebay"]


def test_service_blank_query_returns_empty() -> None:
    service = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()],
    )
    result = service.search("  ")
    assert result.query == ""
    assert result.results == ()
