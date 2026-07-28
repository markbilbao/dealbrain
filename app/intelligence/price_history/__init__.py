"""Price History intelligence package — stored observations only."""

from app.intelligence.price_history.memory import InMemoryPriceHistoryStore
from app.intelligence.price_history.mock_fixture import (
    FALLING_MOCK_SNAPSHOTS,
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    IPHONE_DEMO_CURRENCY,
    IPHONE_DEMO_IDENTITY_KEY,
    MOCK_HISTORY_LABEL,
    RISING_MOCK_SNAPSHOTS,
    STABLE_MOCK_SNAPSHOTS,
    build_iphone_demo_mock_snapshots,
    load_iphone_demo_mock_history,
)
from app.intelligence.price_history.statistics import (
    DEFAULT_TREND_THRESHOLD_PERCENT,
    MIN_OBSERVATIONS_FOR_TREND,
    build_marketplace_summaries,
    calculate_statistics,
    classify_trend,
    ensure_single_currency,
    sort_snapshots,
)

__all__ = [
    "DEFAULT_TREND_THRESHOLD_PERCENT",
    "FALLING_MOCK_SNAPSHOTS",
    "IPHONE_DEMO_CANONICAL_PRODUCT_ID",
    "IPHONE_DEMO_CURRENCY",
    "IPHONE_DEMO_IDENTITY_KEY",
    "InMemoryPriceHistoryStore",
    "MIN_OBSERVATIONS_FOR_TREND",
    "MOCK_HISTORY_LABEL",
    "RISING_MOCK_SNAPSHOTS",
    "STABLE_MOCK_SNAPSHOTS",
    "build_iphone_demo_mock_snapshots",
    "build_marketplace_summaries",
    "calculate_statistics",
    "classify_trend",
    "ensure_single_currency",
    "load_iphone_demo_mock_history",
    "sort_snapshots",
]
