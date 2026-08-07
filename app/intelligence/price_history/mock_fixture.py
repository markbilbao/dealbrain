"""Development-only mock price history for the iPhone demo.

DEVELOPMENT MOCK DATA — NOT LIVE MARKETPLACE HISTORY
====================================================

This module seeds deterministic, fixed-timestamp observations so demos and
tests can exercise rising / falling / stable trend classifications.

Rules:
- Never load automatically in production (``APP_ENV=production``).
- Callers must invoke :func:`load_iphone_demo_mock_history` explicitly.
- Timestamps and prices are fixed constants — never randomized.
- Wording for demos: “Lowest recorded price in the available PiqSavi history.”
  and “Development history uses mocked observations.”
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.domain.exceptions import PriceHistoryValidationError
from app.domain.interfaces.price_history_store import PriceHistoryStore

# Fixed canonical product id for the iPhone 17 Pro Max 256GB Black Titanium demo.
IPHONE_DEMO_CANONICAL_PRODUCT_ID = "00000000-0000-4000-8000-000000000017"
IPHONE_DEMO_IDENTITY_KEY = "apple/iphone/17-pro-max/256gb/black-titanium"
IPHONE_DEMO_CURRENCY = "PHP"

# Marker present on every mock snapshot seller label / docs.
MOCK_HISTORY_LABEL = "DEVELOPMENT_MOCK_PRICE_HISTORY"


def _ts(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def build_iphone_demo_mock_snapshots() -> tuple[PriceSnapshot, ...]:
    """Return fixed mock observations covering rising, falling, and stable segments.

    Timeline (PHP total_cost):
    - Early window rises 73_990 → 76_990 (rising segment in isolation)
    - Mid window falls 76_990 → 73_990 (falling segment in isolation)
    - Late window holds near 74_500–74_999 (stable segment in isolation)
    - Combined series ends lower than the peak → overall falling for full set
    """
    rows: list[tuple[str, str, str | None, float, float, AvailabilityStatus, datetime, str]] = [
        # Rising segment
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            73_990.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 5, 1),
            "aaaaaaaa-0001-4000-8000-000000000001",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            74_200.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 5, 8),
            "aaaaaaaa-0001-4000-8000-000000000002",
        ),
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            75_500.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 5, 15),
            "aaaaaaaa-0001-4000-8000-000000000003",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            76_990.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 5, 22),
            "aaaaaaaa-0001-4000-8000-000000000004",
        ),
        # Falling segment
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            76_490.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 6, 1),
            "aaaaaaaa-0001-4000-8000-000000000005",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            75_200.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 6, 8),
            "aaaaaaaa-0001-4000-8000-000000000006",
        ),
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            74_500.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 6, 15),
            "aaaaaaaa-0001-4000-8000-000000000007",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            73_990.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 6, 22),
            "aaaaaaaa-0001-4000-8000-000000000008",
        ),
        # Stable segment + out-of-stock edge observation
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            74_999.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 7, 1),
            "aaaaaaaa-0001-4000-8000-000000000009",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            74_500.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 7, 8),
            "aaaaaaaa-0001-4000-8000-000000000010",
        ),
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            74_800.0,
            0.0,
            AvailabilityStatus.LIMITED,
            _ts(2026, 7, 15),
            "aaaaaaaa-0001-4000-8000-000000000011",
        ),
        (
            "lazada",
            "2002001",
            "Lazada Apple Store",
            74_500.0,
            0.0,
            AvailabilityStatus.IN_STOCK,
            _ts(2026, 7, 22),
            "aaaaaaaa-0001-4000-8000-000000000012",
        ),
        # Unavailable listing observation (still stored; never fabricated away)
        (
            "shopee",
            "1001001",
            "Apple Authorized PH",
            74_999.0,
            0.0,
            AvailabilityStatus.OUT_OF_STOCK,
            _ts(2026, 7, 25),
            "aaaaaaaa-0001-4000-8000-000000000013",
        ),
    ]

    snapshots: list[PriceSnapshot] = []
    for (
        marketplace,
        listing_id,
        seller,
        item_price,
        shipping,
        availability,
        observed_at,
        snapshot_id,
    ) in rows:
        snapshots.append(
            PriceSnapshot(
                snapshot_id=UUID(snapshot_id),
                canonical_product_id=IPHONE_DEMO_CANONICAL_PRODUCT_ID,
                marketplace=marketplace,
                listing_id=listing_id,
                seller_name=f"{seller} [{MOCK_HISTORY_LABEL}]",
                currency=IPHONE_DEMO_CURRENCY,
                item_price=item_price,
                shipping_cost=shipping,
                total_cost=round(item_price + shipping, 2),
                availability=availability,
                observed_at=observed_at,
            )
        )
    return tuple(snapshots)


# Explicit subsets for unit tests that need a single trend classification.
RISING_MOCK_SNAPSHOTS = build_iphone_demo_mock_snapshots()[0:4]
FALLING_MOCK_SNAPSHOTS = build_iphone_demo_mock_snapshots()[4:8]
STABLE_MOCK_SNAPSHOTS = build_iphone_demo_mock_snapshots()[8:12]


async def load_iphone_demo_mock_history(
    store: PriceHistoryStore,
    *,
    app_env: str,
) -> list[PriceSnapshot]:
    """Seed the iPhone demo mock observations into ``store``.

    Raises :class:`PriceHistoryValidationError` when ``app_env`` is production.
    """
    if app_env == "production":
        raise PriceHistoryValidationError(
            "Development mock price history must never load in production."
        )
    return await store.save_many(list(build_iphone_demo_mock_snapshots()))
