"""Mock Lazada marketplace collector — canned fixtures only."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.domain.entities.collection import CollectionTarget
from app.intelligence.collection.base import BaseMockCollector
from app.intelligence.marketplace.lazada.connector import LazadaConnector
from app.intelligence.marketplace.lazada.mock_data import LAZADA_MOCK_LISTINGS


class MockLazadaCollector(BaseMockCollector):
    """Development-only Lazada collector using existing mock listing fixtures."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[CollectionTarget, datetime], str] | None = None,
    ) -> None:
        connector = LazadaConnector()
        super().__init__(
            marketplace_name="lazada",
            fixtures=LAZADA_MOCK_LISTINGS,
            normalize=connector.normalize_listing,
            clock=clock,
            run_id_factory=run_id_factory,
        )
