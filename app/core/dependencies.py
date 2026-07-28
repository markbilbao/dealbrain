"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
from app.infrastructure.database.repositories.canonical_product_repository import (
    SqlAlchemyCanonicalProductStore,
)
from app.infrastructure.database.repositories.price_history_repository import (
    SQLAlchemyPriceHistoryStore,
)
from app.infrastructure.database.repositories.product_repository import ProductRepository
from app.infrastructure.database.session import get_db_session
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from app.services.product_service import ProductService
from app.services.shopping_recommendation_service import ShoppingRecommendationService

# Process-scoped in-memory registry for demo / local runs without Postgres.
_MEMORY_CANONICAL_STORE = InMemoryCanonicalProductStore()
_MEMORY_PRICE_HISTORY_STORE = InMemoryPriceHistoryStore()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request scope."""
    async for session in get_db_session():
        yield session


def get_product_repository(
    session: AsyncSession = Depends(get_db),
) -> ProductRepository:
    """Provide a product repository bound to the request session."""
    return ProductRepository(session)


def get_product_service(
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    """Provide the product application service."""
    return ProductService(repository)


def get_product_parser() -> ProductIntelligenceEngine:
    """Provide the deterministic Product Intelligence parser."""
    return RuleBasedProductParser()


async def get_canonical_product_store() -> AsyncGenerator[CanonicalProductStore, None]:
    """Provide the Canonical Product Registry persistence adapter.

    Defaults to an in-memory store for the Product Intelligence demo (no DB).
    Set ``CANONICAL_REGISTRY_BACKEND=sqlalchemy`` to use Postgres.
    """
    if settings.canonical_registry_backend == "sqlalchemy":
        async for session in get_db_session():
            yield SqlAlchemyCanonicalProductStore(session)
            return
    yield _MEMORY_CANONICAL_STORE


def get_canonical_product_registry(
    store: CanonicalProductStore = Depends(get_canonical_product_store),
) -> CanonicalProductRegistry:
    """Provide the Canonical Product Registry service."""
    return CanonicalProductRegistryService(store)


def get_product_matcher() -> ProductMatcher:
    """Provide the deterministic Product Matching Engine."""
    return ExactVariantProductMatcher()


def get_product_intelligence_service(
    parser: ProductIntelligenceEngine = Depends(get_product_parser),
    registry: CanonicalProductRegistry = Depends(get_canonical_product_registry),
    matcher: ProductMatcher = Depends(get_product_matcher),
) -> ProductIntelligenceService:
    """Provide the Product Intelligence orchestration service."""
    return ProductIntelligenceService(parser=parser, registry=registry, matcher=matcher)


def get_marketplace_connectors() -> list[MarketplaceConnector]:
    """Provide registered marketplace connectors (mocked Sprint 4 adapters)."""
    return [ShopeeConnector(), LazadaConnector()]


def get_marketplace_intelligence_service(
    connectors: list[MarketplaceConnector] = Depends(get_marketplace_connectors),
) -> MarketplaceIntelligenceService:
    """Provide the Marketplace Intelligence orchestration service."""
    return MarketplaceIntelligenceService(connectors=connectors)


def get_deal_score_engine() -> DealScoreEngine:
    """Provide the deterministic weighted DealScore engine."""
    return WeightedDealScoreEngine()


def get_deal_recommendation_service(
    marketplace_service: MarketplaceIntelligenceService = Depends(
        get_marketplace_intelligence_service
    ),
    deal_score_engine: DealScoreEngine = Depends(get_deal_score_engine),
) -> DealRecommendationService:
    """Provide the DealScore recommendation orchestration service."""
    return DealRecommendationService(
        marketplace_service=marketplace_service,
        deal_score_engine=deal_score_engine,
    )


def get_recommendation_engine() -> RecommendationEngine:
    """Provide the deterministic rule-based recommendation engine."""
    return RuleBasedRecommendationEngine()


def get_shopping_recommendation_service(
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine),
) -> ShoppingRecommendationService:
    """Provide the shopping recommendation orchestration service."""
    return ShoppingRecommendationService(
        deal_recommendation_service=deal_recommendation_service,
        recommendation_engine=recommendation_engine,
    )


async def get_price_history_store() -> AsyncGenerator[PriceHistoryStore, None]:
    """Provide the Price History persistence adapter.

    Defaults to an in-memory store for local demos. Set
    ``PRICE_HISTORY_BACKEND=sqlalchemy`` to use Postgres.
    """
    if settings.price_history_backend == "sqlalchemy":
        async for session in get_db_session():
            yield SQLAlchemyPriceHistoryStore(session)
            return
    yield _MEMORY_PRICE_HISTORY_STORE


def get_price_history_service(
    store: PriceHistoryStore = Depends(get_price_history_store),
    marketplace_service: MarketplaceIntelligenceService = Depends(
        get_marketplace_intelligence_service
    ),
    product_intelligence_service: ProductIntelligenceService = Depends(
        get_product_intelligence_service
    ),
) -> PriceHistoryService:
    """Provide the Price History orchestration service."""
    seed_mock = settings.price_history_seed_demo_mock and settings.app_env != "production"
    return PriceHistoryService(
        store,
        marketplace_service=marketplace_service,
        product_intelligence_service=product_intelligence_service,
        trend_threshold_percent=settings.price_trend_threshold_percent,
        app_env=settings.app_env,
        seed_demo_mock_on_search=seed_mock,
    )
