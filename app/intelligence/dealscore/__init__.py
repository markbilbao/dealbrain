"""DealScore intelligence package — deterministic deal ranking."""

from app.intelligence.dealscore.engine import DEFAULT_WEIGHTS, WeightedDealScoreEngine
from app.intelligence.dealscore.enrichment import (
    MOCK_DEAL_ATTRIBUTES,
    resolve_deal_attributes,
    to_scoreable_listing,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "MOCK_DEAL_ATTRIBUTES",
    "WeightedDealScoreEngine",
    "resolve_deal_attributes",
    "to_scoreable_listing",
]
