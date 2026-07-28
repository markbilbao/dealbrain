"""Mock Shopee marketplace collector — canned fixtures only."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.domain.entities.collection import CollectionTarget
from app.intelligence.collection.base import BaseMockCollector
from app.intelligence.marketplace.shopee.connector import ShopeeConnector
from app.intelligence.marketplace.shopee.mock_data import SHOPEE_MOCK_LISTINGS


class MockShopeeCollector(BaseMockCollector):
    """Development-only Shopee collector using existing mock listing fixtures."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[CollectionTarget, datetime], str] | None = None,
    ) -> None:
        connector = ShopeeConnector()
        super().__init__(
            marketplace_name="shopee",
            fixtures=SHOPEE_MOCK_LISTINGS,
            normalize=connector.normalize_listing,
            clock=clock,
            run_id_factory=run_id_factory,
        )
