"""Domain port interfaces (abstract contracts for infrastructure adapters)."""

from app.domain.interfaces.ai_provider import AIProvider
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.domain.interfaces.collection_job_repository import (
    CollectionJobRepository,
    CollectionRunRepository,
)
from app.domain.interfaces.collection_scheduler import CollectionScheduler
from app.domain.interfaces.deal_score_engine import DealScoreEngine
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.domain.interfaces.marketplace_rate_limiter import (
    MarketplaceRateLimiter,
    RateLimitDecision,
)
from app.domain.interfaces.notification_service import NotificationService
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.domain.interfaces.repository import Repository
from app.domain.interfaces.watchlist_repository import (
    AlertRepository,
    WatchlistRepository,
)

__all__ = [
    "AIProvider",
    "AlertRepository",
    "CanonicalProductRegistry",
    "CanonicalProductStore",
    "CollectionJobRepository",
    "CollectionRunRepository",
    "CollectionScheduler",
    "DealScoreEngine",
    "MarketplaceCollector",
    "MarketplaceConnector",
    "MarketplaceRateLimiter",
    "NotificationService",
    "PriceHistoryStore",
    "ProductIntelligenceEngine",
    "ProductMatcher",
    "RateLimitDecision",
    "RecommendationEngine",
    "Repository",
    "WatchlistRepository",
]
