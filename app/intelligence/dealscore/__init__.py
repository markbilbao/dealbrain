"""DealScore intelligence package — deterministic deal ranking."""

from app.intelligence.dealscore.engine import DEFAULT_WEIGHTS, WeightedDealScoreEngine
from app.intelligence.dealscore.enrichment import (
    MOCK_DEAL_ATTRIBUTES,
    MOCK_DEAL_ENRICHMENT_IS_LIVE_EVIDENCE,
    mock_deal_enrichment_is_production_evidence,
    resolve_deal_attributes,
    to_scoreable_listing,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "MOCK_DEAL_ATTRIBUTES",
    "MOCK_DEAL_ENRICHMENT_IS_LIVE_EVIDENCE",
    "WeightedDealScoreEngine",
    "mock_deal_enrichment_is_production_evidence",
    "resolve_deal_attributes",
    "to_scoreable_listing",
]
