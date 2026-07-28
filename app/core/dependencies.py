"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.domain.interfaces.collection_job_repository import CollectionJobRepository
from app.domain.interfaces.collection_scheduler import CollectionScheduler
from app.domain.interfaces.deal_score_engine import DealScoreEngine
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.domain.interfaces.marketplace_rate_limiter import MarketplaceRateLimiter
from app.domain.interfaces.notification_service import NotificationService
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.domain.interfaces.watchlist_repository import (
    AlertRepository,
    WatchlistRepository,
)
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
from app.intelligence.collection import (
    InMemoryCollectionJobRepository,
    InMemoryCollectionScheduler,
    InMemoryMarketplaceRateLimiter,
    MockLazadaCollector,
    MockShopeeCollector,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.intelligence.watchlists import (
    InMemoryWatchlistRepository,
    MockNotificationService,
)
from app.services.alert_service import AlertService
from app.services.collection_operations_service import CollectionOperationsService
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from app.services.product_service import ProductService
from app.services.shopping_recommendation_service import ShoppingRecommendationService
from app.services.watchlist_service import WatchlistService

# Process-scoped in-memory registry for demo / local runs without Postgres.
_MEMORY_CANONICAL_STORE = InMemoryCanonicalProductStore()
_MEMORY_PRICE_HISTORY_STORE = InMemoryPriceHistoryStore()
_MEMORY_COLLECTION_JOB_REPOSITORY = InMemoryCollectionJobRepository()
_MEMORY_COLLECTION_RATE_LIMITER = InMemoryMarketplaceRateLimiter(
    max_requests=100,
    window_seconds=60.0,
)
_MEMORY_WATCHLIST_REPOSITORY = InMemoryWatchlistRepository()
_MOCK_NOTIFICATION_SERVICE = MockNotificationService()
_COLLECTION_SCHEDULER: InMemoryCollectionScheduler | None = None
_COLLECTION_SERVICE: MarketplaceCollectionService | None = None
_COLLECTION_OPERATIONS_SERVICE: CollectionOperationsService | None = None
_WATCHLIST_SERVICE: WatchlistService | None = None
_ALERT_SERVICE: AlertService | None = None


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


def get_marketplace_collectors() -> list[MarketplaceCollector]:
    """Provide registered mock marketplace collectors (no live HTTP)."""
    return [MockShopeeCollector(), MockLazadaCollector()]


def get_collection_job_repository() -> CollectionJobRepository:
    """Provide the process-scoped in-memory collection job repository."""
    return _MEMORY_COLLECTION_JOB_REPOSITORY


def get_marketplace_rate_limiter() -> MarketplaceRateLimiter:
    """Provide the process-scoped in-memory marketplace rate limiter."""
    return _MEMORY_COLLECTION_RATE_LIMITER


def get_marketplace_collection_service(
    collectors: list[MarketplaceCollector] = Depends(get_marketplace_collectors),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    product_intelligence_service: ProductIntelligenceService = Depends(
        get_product_intelligence_service
    ),
    repository: CollectionJobRepository = Depends(get_collection_job_repository),
    rate_limiter: MarketplaceRateLimiter = Depends(get_marketplace_rate_limiter),
) -> MarketplaceCollectionService:
    """Provide the Marketplace Collection orchestration service."""
    global _COLLECTION_SERVICE
    # Reuse a process-scoped service so the scheduler callback stays consistent
    # with the same repository and collectors for the demo process.
    if _COLLECTION_SERVICE is None:
        _COLLECTION_SERVICE = MarketplaceCollectionService(
            collectors,
            price_history_service=price_history_service,
            product_intelligence_service=product_intelligence_service,
            repository=repository,
            rate_limiter=rate_limiter,
        )
        return _COLLECTION_SERVICE

    # Refresh collaborator references that may be request-scoped (SQLAlchemy).
    _COLLECTION_SERVICE._price_history = price_history_service  # noqa: SLF001
    _COLLECTION_SERVICE._product_intelligence = product_intelligence_service  # noqa: SLF001
    return _COLLECTION_SERVICE


def get_collection_scheduler(
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
    repository: CollectionJobRepository = Depends(get_collection_job_repository),
) -> CollectionScheduler:
    """Provide the deterministic in-memory collection scheduler."""
    global _COLLECTION_SCHEDULER
    if _COLLECTION_SCHEDULER is None:
        _COLLECTION_SCHEDULER = InMemoryCollectionScheduler(
            repository,
            run_job=service.run_job,
        )
    else:
        _COLLECTION_SCHEDULER._run_job = service.run_job  # noqa: SLF001
    return _COLLECTION_SCHEDULER


def get_collection_operations_service(
    collection_service: MarketplaceCollectionService = Depends(
        get_marketplace_collection_service
    ),
    repository: CollectionJobRepository = Depends(get_collection_job_repository),
    scheduler: CollectionScheduler = Depends(get_collection_scheduler),
    collectors: list[MarketplaceCollector] = Depends(get_marketplace_collectors),
    store: PriceHistoryStore = Depends(get_price_history_store),
) -> CollectionOperationsService:
    """Provide the Collection Operations control-plane service."""
    global _COLLECTION_OPERATIONS_SERVICE
    if _COLLECTION_OPERATIONS_SERVICE is None:
        _COLLECTION_OPERATIONS_SERVICE = CollectionOperationsService(
            collection_service=collection_service,
            repository=repository,
            run_repository=repository,  # type: ignore[arg-type]
            scheduler=scheduler,
            collectors=collectors,
            price_history_store=store,
        )
        return _COLLECTION_OPERATIONS_SERVICE

    _COLLECTION_OPERATIONS_SERVICE._collection = collection_service  # noqa: SLF001
    _COLLECTION_OPERATIONS_SERVICE._scheduler = scheduler  # noqa: SLF001
    _COLLECTION_OPERATIONS_SERVICE._price_history_store = store  # noqa: SLF001
    return _COLLECTION_OPERATIONS_SERVICE


def get_watchlist_repository() -> WatchlistRepository:
    """Provide the process-scoped in-memory watchlist repository."""
    return _MEMORY_WATCHLIST_REPOSITORY


def get_alert_repository() -> AlertRepository:
    """Provide the process-scoped in-memory alert repository."""
    return _MEMORY_WATCHLIST_REPOSITORY


def get_notification_service() -> NotificationService:
    """Provide the mock notification service (queued status only)."""
    return _MOCK_NOTIFICATION_SERVICE


def get_watchlist_service(
    repository: WatchlistRepository = Depends(get_watchlist_repository),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
    registry: CanonicalProductRegistry = Depends(get_canonical_product_registry),
) -> WatchlistService:
    """Provide the Watchlist orchestration service."""
    global _WATCHLIST_SERVICE
    if _WATCHLIST_SERVICE is None:
        _WATCHLIST_SERVICE = WatchlistService(
            repository,
            price_history_service=price_history_service,
            deal_recommendation_service=deal_recommendation_service,
            canonical_registry=registry,
        )
        return _WATCHLIST_SERVICE

    _WATCHLIST_SERVICE._price_history = price_history_service  # noqa: SLF001
    _WATCHLIST_SERVICE._deal_recommendation = deal_recommendation_service  # noqa: SLF001
    _WATCHLIST_SERVICE._registry = registry  # noqa: SLF001
    return _WATCHLIST_SERVICE


def get_alert_service(
    repository: WatchlistRepository = Depends(get_watchlist_repository),
    alert_repository: AlertRepository = Depends(get_alert_repository),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    notification_service: NotificationService = Depends(get_notification_service),
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
) -> AlertService:
    """Provide the Alert evaluation service."""
    global _ALERT_SERVICE
    if _ALERT_SERVICE is None:
        _ALERT_SERVICE = AlertService(
            repository,
            alert_repository,
            price_history_service=price_history_service,
            notification_service=notification_service,
            deal_recommendation_service=deal_recommendation_service,
        )
        return _ALERT_SERVICE

    _ALERT_SERVICE._price_history = price_history_service  # noqa: SLF001
    _ALERT_SERVICE._notifications = notification_service  # noqa: SLF001
    _ALERT_SERVICE._deal_recommendation = deal_recommendation_service  # noqa: SLF001
    return _ALERT_SERVICE
