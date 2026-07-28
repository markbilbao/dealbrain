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
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.infrastructure.database.repositories.canonical_product_repository import (
    SqlAlchemyCanonicalProductStore,
)
from app.infrastructure.database.repositories.product_repository import ProductRepository
from app.infrastructure.database.session import get_db_session
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.product_intelligence_service import ProductIntelligenceService
from app.services.product_service import ProductService
from app.services.shopping_recommendation_service import ShoppingRecommendationService

# Process-scoped in-memory registry for demo / local runs without Postgres.
_MEMORY_CANONICAL_STORE = InMemoryCanonicalProductStore()


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
