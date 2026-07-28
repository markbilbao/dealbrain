"""Domain port interfaces (abstract contracts for infrastructure adapters)."""

from app.domain.interfaces.ai_provider import AIProvider
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.domain.interfaces.deal_score_engine import DealScoreEngine
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.domain.interfaces.repository import Repository

__all__ = [
    "AIProvider",
    "CanonicalProductRegistry",
    "CanonicalProductStore",
    "DealScoreEngine",
    "MarketplaceConnector",
    "PriceHistoryStore",
    "ProductIntelligenceEngine",
    "ProductMatcher",
    "RecommendationEngine",
    "Repository",
]
