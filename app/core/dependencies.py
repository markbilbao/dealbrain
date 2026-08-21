"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.affiliate.memory import InMemoryAffiliateRepository
from app.alerts.memory import InMemoryAlertRuleRepository
from app.core.config import settings
from app.domain.interfaces.alert_rule_repository import AlertEventRepository, AlertRuleRepository
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.domain.interfaces.collection_job_repository import CollectionJobRepository
from app.domain.interfaces.collection_scheduler import CollectionScheduler
from app.domain.interfaces.deal_score_engine import DealScoreEngine
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.domain.interfaces.marketplace_rate_limiter import MarketplaceRateLimiter
from app.domain.interfaces.notification_center_repository import NotificationCenterRepository
from app.domain.interfaces.notification_service import NotificationService
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.domain.interfaces.product_matcher import ProductMatcher
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.domain.interfaces.review_repository import ReviewCollector, ReviewRepository
from app.domain.interfaces.review_summary_repository import (
    ReviewSummarizer,
    ReviewSummaryRepository,
)
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.domain.interfaces.watchlist_repository import (
    AlertRepository,
    WatchlistRepository,
)
from app.infrastructure.ai.community_providers import (
    ClaudeCommunityProvider,
    DeterministicCommunityProviderAdapter,
    GeminiCommunityProvider,
    OpenAICommunityProvider,
)
from app.infrastructure.ai.review_providers import (
    ClaudeReviewProvider,
    DeterministicReviewProvider,
    GeminiReviewProvider,
    OpenAIReviewProvider,
)
from app.infrastructure.ai.shopping_providers import (
    ClaudeShoppingProvider,
    DeterministicShoppingProviderAdapter,
    GeminiShoppingProvider,
    OpenAIShoppingProvider,
)
from app.infrastructure.ai.transports import DisabledTransport
from app.infrastructure.community import (
    AmazonQACommunityProvider,
    DiscordCommunityProvider,
    ManufacturerForumsCommunityProvider,
    MarketplaceQuestionsCommunityProvider,
    MockCommunityTransport,
    RedditCommunityProvider,
    YouTubeCommunityProvider,
)
from app.infrastructure.database.repositories.canonical_product_repository import (
    SqlAlchemyCanonicalProductStore,
)
from app.infrastructure.database.repositories.price_history_repository import (
    SQLAlchemyPriceHistoryStore,
)
from app.infrastructure.database.repositories.product_repository import ProductRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
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
from app.intelligence.community import (
    CommunityAIOrchestrator,
    CommunityOrchestrator,
    CommunityRegistry,
    CommunitySummaryRegistry,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.intelligence.review_summary import (
    DeterministicMockReviewSummarizer,
    InMemoryReviewSummaryRepository,
)
from app.intelligence.review_summary.orchestrator import MultiModelReviewOrchestrator
from app.intelligence.review_summary.registry import AIProviderRegistry
from app.intelligence.reviews import (
    InMemoryReviewRepository,
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.intelligence.shopping_assistant import (
    InMemoryConversationRepository,
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.intelligence.watchlists import (
    MockNotificationService,
)
from app.launch.cache import TtlCache
from app.launch.feature_flags import FeatureFlagRegistry, get_feature_flags
from app.launch.fixtures import DemoLauncherState
from app.launch.memory import InMemoryLaunchStore
from app.launch.rate_limit import ConfigurableRateLimiter, RateLimitRule
from app.marketplace import (
    FixtureMarketplaceConnector,
    ImportedMarketplaceConnector,
    InMemoryMarketplaceDataRepository,
    MarketplaceConnectorRegistry,
    MockLiveMarketplaceConnector,
)
from app.merchant.memory import InMemoryMerchantRepository
from app.notifications.delivery import EnhancedNotificationService
from app.notifications.memory import InMemoryNotificationCenterRepository
from app.services.affiliate_disclosure_service import AffiliateDisclosureService
from app.services.affiliate_link_service import AffiliateLinkService
from app.services.affiliate_merchant_service import AffiliateMerchantService
from app.services.affiliate_reporting_service import AffiliateReportingService
from app.services.affiliate_tracking_service import AffiliateTrackingService
from app.services.alert_evaluation_service import AlertEvaluationService
from app.services.alert_rule_service import AlertRuleService
from app.services.alert_service import AlertService
from app.services.collection_operations_service import CollectionOperationsService
from app.services.community_intelligence_service import CommunityIntelligenceService
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.launch_config_service import LaunchConfigService
from app.services.launch_dashboard_service import LaunchDashboardService
from app.services.launch_demo_service import LaunchDemoService
from app.services.launch_health_service import LaunchHealthService
from app.services.launch_performance_service import LaunchPerformanceService
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.merchant_admin_service import MerchantAdminService
from app.services.merchant_analytics_service import MerchantAnalyticsService
from app.services.merchant_auth_service import MerchantAuthService
from app.services.merchant_campaign_service import MerchantCampaignService
from app.services.merchant_membership_service import MerchantMembershipService
from app.services.merchant_offer_service import MerchantOfferService
from app.services.merchant_organization_service import MerchantOrganizationService
from app.services.merchant_product_service import MerchantProductService
from app.services.merchant_promotion_service import MerchantPromotionService
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.personal_agent_service import PersonalAgentService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.services.review_summary_service import ReviewSummaryService
from app.services.shopping_assistant_service import ShoppingAssistantService
from app.services.shopping_recommendation_service import ShoppingRecommendationService
from app.services.user_dashboard_service import UserDashboardService
from app.services.user_platform_service import UserPlatformService
from app.services.watchlist_service import WatchlistService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.watchlists.memory import InMemoryWatchlistStore
from app.watchlists.security import WatchlistAuditLogger

# Process-scoped in-memory registry for demo / local runs without Postgres.
_MEMORY_CANONICAL_STORE = InMemoryCanonicalProductStore()
_MEMORY_PRICE_HISTORY_STORE = InMemoryPriceHistoryStore()
_MEMORY_COLLECTION_JOB_REPOSITORY = InMemoryCollectionJobRepository()
_MEMORY_COLLECTION_RATE_LIMITER = InMemoryMarketplaceRateLimiter(
    max_requests=100,
    window_seconds=60.0,
)
_MEMORY_WATCHLIST_REPOSITORY = InMemoryWatchlistStore()
_MEMORY_ALERT_RULE_REPOSITORY = InMemoryAlertRuleRepository()
_MEMORY_NOTIFICATION_CENTER_REPOSITORY = InMemoryNotificationCenterRepository()
_MEMORY_AFFILIATE_REPOSITORY = InMemoryAffiliateRepository()
_MEMORY_MERCHANT_REPOSITORY = InMemoryMerchantRepository()
_SQL_USER_PLATFORM_STORE = None
_SQL_MARKETPLACE_DATA_REPOSITORY = None
_SQL_ALERT_RULE_REPOSITORY = None
_SQL_NOTIFICATION_CENTER_REPOSITORY = None
_SQL_AFFILIATE_REPOSITORY = None
_SQL_MERCHANT_REPOSITORY = None
_WATCHLIST_AUDIT_LOGGER = WatchlistAuditLogger()
_MEMORY_REVIEW_REPOSITORY = InMemoryReviewRepository()
_MEMORY_REVIEW_SUMMARY_REPOSITORY = InMemoryReviewSummaryRepository()
_MEMORY_SHOPPING_CONVERSATION_REPOSITORY = InMemoryConversationRepository(
    ttl_seconds=settings.ai_shopping_conversation_ttl_seconds,
)
_MEMORY_SHOPPING_DECISION_SNAPSHOT_REPOSITORY = InMemoryDecisionSnapshotRepository()
_MOCK_NOTIFICATION_SERVICE = MockNotificationService()
_COLLECTION_SCHEDULER: InMemoryCollectionScheduler | None = None
_COLLECTION_SERVICE: MarketplaceCollectionService | None = None
_COLLECTION_OPERATIONS_SERVICE: CollectionOperationsService | None = None
_WATCHLIST_SERVICE: WatchlistService | None = None
_ALERT_SERVICE: AlertService | None = None
_ALERT_RULE_SERVICE: AlertRuleService | None = None
_ALERT_EVALUATION_SERVICE: AlertEvaluationService | None = None
_NOTIFICATION_CENTER_SERVICE: NotificationCenterService | None = None
_NOTIFICATION_PREFERENCE_SERVICE: NotificationPreferenceService | None = None
_ENHANCED_NOTIFICATION_SERVICE: EnhancedNotificationService | None = None
_USER_DASHBOARD_SERVICE: UserDashboardService | None = None
_AFFILIATE_MERCHANT_SERVICE: AffiliateMerchantService | None = None
_AFFILIATE_LINK_SERVICE: AffiliateLinkService | None = None
_AFFILIATE_TRACKING_SERVICE: AffiliateTrackingService | None = None
_AFFILIATE_REPORTING_SERVICE: AffiliateReportingService | None = None
_AFFILIATE_DISCLOSURE_SERVICE: AffiliateDisclosureService | None = None
_MERCHANT_AUTH_SERVICE: MerchantAuthService | None = None
_MERCHANT_ORGANIZATION_SERVICE: MerchantOrganizationService | None = None
_MERCHANT_MEMBERSHIP_SERVICE: MerchantMembershipService | None = None
_MERCHANT_PRODUCT_SERVICE: MerchantProductService | None = None
_MERCHANT_OFFER_SERVICE: MerchantOfferService | None = None
_MERCHANT_PROMOTION_SERVICE: MerchantPromotionService | None = None
_MERCHANT_CAMPAIGN_SERVICE: MerchantCampaignService | None = None
_MERCHANT_ANALYTICS_SERVICE: MerchantAnalyticsService | None = None
_MERCHANT_ADMIN_SERVICE: MerchantAdminService | None = None
_REVIEW_SERVICE: ReviewService | None = None
_REVIEW_SUMMARY_SERVICE: ReviewSummaryService | None = None
_SHOPPING_ASSISTANT_SERVICE: ShoppingAssistantService | None = None
_COMMUNITY_INTELLIGENCE_SERVICE: CommunityIntelligenceService | None = None
_KNOWLEDGE_GRAPH_SERVICE: KnowledgeGraphService | None = None
_KNOWLEDGE_GRAPH_REPOSITORY = None
_PERSONAL_AGENT_SERVICE: PersonalAgentService | None = None
_PERSONAL_PROFILE_REPOSITORY = None
_USER_PLATFORM_STORE = None
_USER_PLATFORM_SERVICE: UserPlatformService | None = None
_EARLY_ACCESS_SERVICE = None
_MARKETPLACE_DATA_REPOSITORY = InMemoryMarketplaceDataRepository()
_MARKETPLACE_DATA_SERVICE: MarketplaceDataService | None = None
_MARKETPLACE_CONNECTOR_REGISTRY: MarketplaceConnectorRegistry | None = None

# Sprint 22 — launch readiness
_LAUNCH_STORE = InMemoryLaunchStore()
_DEMO_LAUNCHER_STATE = DemoLauncherState()
_PERFORMANCE_CACHE = TtlCache(
    default_ttl_seconds=settings.performance_cache_ttl_seconds,
    enabled=settings.performance_cache_enabled,
)
_RATE_LIMITER = ConfigurableRateLimiter(
    {
        "default": RateLimitRule("default", settings.rate_limit_default_per_minute, 60),
        "login": RateLimitRule("login", settings.rate_limit_login_per_minute, 60),
        "registration": RateLimitRule(
            "registration", settings.rate_limit_registration_per_minute, 60
        ),
        "early_access_events": RateLimitRule(
            "early_access_events",
            settings.rate_limit_early_access_events_per_minute,
            60,
        ),
        "affiliate": RateLimitRule("affiliate", settings.rate_limit_affiliate_per_minute, 60),
        "merchant": RateLimitRule("merchant", settings.rate_limit_merchant_per_minute, 60),
        "search": RateLimitRule("search", settings.rate_limit_search_per_minute, 60),
        "recommendations": RateLimitRule(
            "recommendations", settings.rate_limit_recommendations_per_minute, 60
        ),
    },
    enabled=settings.rate_limiting_enabled,
)
_LAUNCH_HEALTH_SERVICE: LaunchHealthService | None = None
_LAUNCH_DASHBOARD_SERVICE: LaunchDashboardService | None = None
_LAUNCH_DEMO_SERVICE: LaunchDemoService | None = None
_LAUNCH_CONFIG_SERVICE: LaunchConfigService | None = None
_LAUNCH_PERFORMANCE_SERVICE: LaunchPerformanceService | None = None


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


def get_marketplace_connector_registry() -> MarketplaceConnectorRegistry:
    """Provide the process-scoped marketplace data connector registry."""
    global _MARKETPLACE_CONNECTOR_REGISTRY
    if _MARKETPLACE_CONNECTOR_REGISTRY is None:
        registry = MarketplaceConnectorRegistry(register_stubs=True)
        registry.register(FixtureMarketplaceConnector())
        registry.register(
            ImportedMarketplaceConnector(
                lambda: get_marketplace_data_repository().list_offers(limit=10_000)
            )
        )
        registry.register(MockLiveMarketplaceConnector())
        _MARKETPLACE_CONNECTOR_REGISTRY = registry
    return _MARKETPLACE_CONNECTOR_REGISTRY


def get_marketplace_data_repository():
    """Provide marketplace data repository (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _SQL_MARKETPLACE_DATA_REPOSITORY
    if resolve_backend("marketplace_data") == "sqlalchemy":
        if _SQL_MARKETPLACE_DATA_REPOSITORY is None:
            from app.infrastructure.database.repositories.marketplace_data_repository import (
                SqlAlchemyMarketplaceDataRepository,
            )

            _SQL_MARKETPLACE_DATA_REPOSITORY = SqlAlchemyMarketplaceDataRepository()
        return _SQL_MARKETPLACE_DATA_REPOSITORY
    return _MARKETPLACE_DATA_REPOSITORY


def get_marketplace_data_service(
    repository=Depends(get_marketplace_data_repository),
    registry: MarketplaceConnectorRegistry = Depends(get_marketplace_connector_registry),
) -> MarketplaceDataService:
    """Provide Marketplace Data Synchronization orchestration."""
    global _MARKETPLACE_DATA_SERVICE
    if _MARKETPLACE_DATA_SERVICE is None:
        _MARKETPLACE_DATA_SERVICE = MarketplaceDataService(
            repository,
            registry,
            require_auth_for_ops=settings.marketplace_data_require_auth,
        )
    return _MARKETPLACE_DATA_SERVICE


def get_deal_recommendation_service(
    marketplace_service: MarketplaceIntelligenceService = Depends(
        get_marketplace_intelligence_service
    ),
    deal_score_engine: DealScoreEngine = Depends(get_deal_score_engine),
    marketplace_data_service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> DealRecommendationService:
    """Provide the DealScore recommendation orchestration service."""
    data = marketplace_data_service if settings.marketplace_data_enabled else None
    return DealRecommendationService(
        marketplace_service=marketplace_service,
        deal_score_engine=deal_score_engine,
        marketplace_data_service=data,
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
    collection_service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
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


def get_watchlist_audit_logger() -> WatchlistAuditLogger:
    """Provide the process-scoped watchlist audit logger (Sprint 19)."""
    return _WATCHLIST_AUDIT_LOGGER


def get_watchlist_service(
    repository: WatchlistRepository = Depends(get_watchlist_repository),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
    registry: CanonicalProductRegistry = Depends(get_canonical_product_registry),
    audit_logger: WatchlistAuditLogger = Depends(get_watchlist_audit_logger),
) -> WatchlistService:
    """Provide the Watchlist orchestration service (Sprint 19-extended)."""
    global _WATCHLIST_SERVICE
    if _WATCHLIST_SERVICE is None:
        _WATCHLIST_SERVICE = ExtendedWatchlistService(
            repository,
            price_history_service=price_history_service,
            deal_recommendation_service=deal_recommendation_service,
            canonical_registry=registry,
            audit_logger=audit_logger,
        )
        return _WATCHLIST_SERVICE

    _WATCHLIST_SERVICE._price_history = price_history_service  # noqa: SLF001
    _WATCHLIST_SERVICE._deal_recommendation = deal_recommendation_service  # noqa: SLF001
    _WATCHLIST_SERVICE._registry = registry  # noqa: SLF001
    return _WATCHLIST_SERVICE


def get_extended_watchlist_service(
    service: WatchlistService = Depends(get_watchlist_service),
) -> ExtendedWatchlistService:
    """Provide the Watchlist service, typed as its Sprint 19 extension.

    ``get_watchlist_service`` always constructs an :class:`ExtendedWatchlistService`
    (see above); this alias exists for call sites that want that Sprint
    19-specific type in their signature.
    """
    assert isinstance(service, ExtendedWatchlistService)  # noqa: S101 - DI wiring invariant
    return service


def get_alert_rule_repository() -> AlertRuleRepository:
    """Provide alert rule repository (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _SQL_ALERT_RULE_REPOSITORY
    if resolve_backend("alerts") == "sqlalchemy":
        if _SQL_ALERT_RULE_REPOSITORY is None:
            from app.infrastructure.database.repositories.alert_repository import (
                SqlAlchemyAlertRuleRepository,
            )

            _SQL_ALERT_RULE_REPOSITORY = SqlAlchemyAlertRuleRepository()
        return _SQL_ALERT_RULE_REPOSITORY
    return _MEMORY_ALERT_RULE_REPOSITORY


def get_alert_event_repository() -> AlertEventRepository:
    """Provide alert event repository (same store as alert rules)."""
    return get_alert_rule_repository()  # type: ignore[return-value]


def get_notification_center_repository() -> NotificationCenterRepository:
    """Provide Notification Center repository (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _SQL_NOTIFICATION_CENTER_REPOSITORY
    if resolve_backend("notifications") == "sqlalchemy":
        if _SQL_NOTIFICATION_CENTER_REPOSITORY is None:
            from app.infrastructure.database.repositories.notification_repository import (
                SqlAlchemyNotificationCenterRepository,
            )

            _SQL_NOTIFICATION_CENTER_REPOSITORY = SqlAlchemyNotificationCenterRepository()
        return _SQL_NOTIFICATION_CENTER_REPOSITORY
    return _MEMORY_NOTIFICATION_CENTER_REPOSITORY


def get_notification_preference_service(
    repository: NotificationCenterRepository = Depends(get_notification_center_repository),
) -> NotificationPreferenceService:
    """Provide the Notification Preference service (Sprint 19)."""
    global _NOTIFICATION_PREFERENCE_SERVICE
    if _NOTIFICATION_PREFERENCE_SERVICE is None:
        _NOTIFICATION_PREFERENCE_SERVICE = NotificationPreferenceService(repository)
    return _NOTIFICATION_PREFERENCE_SERVICE


def get_notification_center_service(
    repository: NotificationCenterRepository = Depends(get_notification_center_repository),
    preference_service: NotificationPreferenceService = Depends(
        get_notification_preference_service
    ),
) -> NotificationCenterService:
    """Provide the Notification Center application service (Sprint 19)."""
    global _NOTIFICATION_CENTER_SERVICE
    if _NOTIFICATION_CENTER_SERVICE is None:
        _NOTIFICATION_CENTER_SERVICE = NotificationCenterService(
            repository, preference_service=preference_service
        )
        return _NOTIFICATION_CENTER_SERVICE
    _NOTIFICATION_CENTER_SERVICE._preferences = preference_service  # noqa: SLF001
    return _NOTIFICATION_CENTER_SERVICE


def get_enhanced_notification_service(
    notification_center_service: NotificationCenterService = Depends(
        get_notification_center_service
    ),
) -> EnhancedNotificationService:
    """Provide the Sprint 19 notification adapter, fanning out to the Notification Center."""
    global _ENHANCED_NOTIFICATION_SERVICE
    center = notification_center_service if settings.watchlists_alerts_enabled else None
    if _ENHANCED_NOTIFICATION_SERVICE is None:
        _ENHANCED_NOTIFICATION_SERVICE = EnhancedNotificationService(
            notification_center_service=center
        )
        return _ENHANCED_NOTIFICATION_SERVICE
    _ENHANCED_NOTIFICATION_SERVICE._notification_center = center  # noqa: SLF001
    return _ENHANCED_NOTIFICATION_SERVICE


def get_alert_rule_service(
    repository: AlertRuleRepository = Depends(get_alert_rule_repository),
    watchlist_repository: WatchlistRepository = Depends(get_watchlist_repository),
) -> AlertRuleService:
    """Provide the Alert Rule CRUD service (Sprint 19)."""
    global _ALERT_RULE_SERVICE
    if _ALERT_RULE_SERVICE is None:
        _ALERT_RULE_SERVICE = AlertRuleService(
            repository, watchlist_repository=watchlist_repository
        )
    return _ALERT_RULE_SERVICE


def get_alert_evaluation_service(
    rule_repository: AlertRuleRepository = Depends(get_alert_rule_repository),
    watchlist_repository: WatchlistRepository = Depends(get_watchlist_repository),
    event_repository: AlertEventRepository = Depends(get_alert_event_repository),
    alert_repository: AlertRepository = Depends(get_alert_repository),
    notification_service: EnhancedNotificationService = Depends(get_enhanced_notification_service),
    notification_center_service: NotificationCenterService = Depends(
        get_notification_center_service
    ),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
    marketplace_data_service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> AlertEvaluationService:
    """Provide the rule-driven Alert Evaluation orchestration service (Sprint 19)."""
    global _ALERT_EVALUATION_SERVICE
    center = notification_center_service if settings.watchlists_alerts_enabled else None
    market_data = marketplace_data_service if settings.marketplace_data_enabled else None
    if _ALERT_EVALUATION_SERVICE is None:
        _ALERT_EVALUATION_SERVICE = AlertEvaluationService(
            rule_repository,
            watchlist_repository,
            event_repository=event_repository,
            alert_repository=alert_repository,
            notification_service=notification_service,
            notification_center_service=center,
            price_history_service=price_history_service,
            deal_recommendation_service=deal_recommendation_service,
            marketplace_data_service=market_data,
        )
        return _ALERT_EVALUATION_SERVICE

    _ALERT_EVALUATION_SERVICE._price_history = price_history_service  # noqa: SLF001
    _ALERT_EVALUATION_SERVICE._deal_recommendation = deal_recommendation_service  # noqa: SLF001
    _ALERT_EVALUATION_SERVICE._marketplace_data = market_data  # noqa: SLF001
    _ALERT_EVALUATION_SERVICE._notification_center = center  # noqa: SLF001
    return _ALERT_EVALUATION_SERVICE


def get_alert_service(
    repository: WatchlistRepository = Depends(get_watchlist_repository),
    alert_repository: AlertRepository = Depends(get_alert_repository),
    price_history_service: PriceHistoryService = Depends(get_price_history_service),
    notification_service: NotificationService = Depends(get_notification_service),
    deal_recommendation_service: DealRecommendationService = Depends(
        get_deal_recommendation_service
    ),
    notification_center_service: NotificationCenterService = Depends(
        get_notification_center_service
    ),
    marketplace_data_service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> AlertService:
    """Provide the Alert evaluation service."""
    global _ALERT_SERVICE
    center = notification_center_service if settings.watchlists_alerts_enabled else None
    market_data = marketplace_data_service if settings.marketplace_data_enabled else None
    if _ALERT_SERVICE is None:
        _ALERT_SERVICE = AlertService(
            repository,
            alert_repository,
            price_history_service=price_history_service,
            notification_service=notification_service,
            deal_recommendation_service=deal_recommendation_service,
            notification_center_service=center,
            marketplace_data_service=market_data,
        )
        return _ALERT_SERVICE

    _ALERT_SERVICE._price_history = price_history_service  # noqa: SLF001
    _ALERT_SERVICE._notifications = notification_service  # noqa: SLF001
    _ALERT_SERVICE._deal_recommendation = deal_recommendation_service  # noqa: SLF001
    _ALERT_SERVICE._notification_center = center  # noqa: SLF001
    _ALERT_SERVICE._marketplace_data = market_data  # noqa: SLF001
    return _ALERT_SERVICE


def get_review_collectors() -> list[ReviewCollector]:
    """Provide registered mock review collectors (no live HTTP / scraping)."""
    return [
        MockShopeeReviewCollector(),
        MockLazadaReviewCollector(),
        MockTikTokShopReviewCollector(),
        MockAmazonReviewCollector(),
    ]


def get_review_repository() -> ReviewRepository:
    """Provide the process-scoped in-memory review repository."""
    return _MEMORY_REVIEW_REPOSITORY


def get_review_service(
    repository: ReviewRepository = Depends(get_review_repository),
    collectors: list[ReviewCollector] = Depends(get_review_collectors),
) -> ReviewService:
    """Provide the Review Intelligence orchestration service."""
    global _REVIEW_SERVICE
    if _REVIEW_SERVICE is None:
        _REVIEW_SERVICE = ReviewService(repository, collectors)
        return _REVIEW_SERVICE
    # Keep the process-scoped service; refresh collectors if DI rebuilds them.
    _REVIEW_SERVICE._collectors = list(collectors)  # noqa: SLF001
    return _REVIEW_SERVICE


def get_review_summary_repository() -> ReviewSummaryRepository:
    """Provide the process-scoped in-memory review summary repository."""
    return _MEMORY_REVIEW_SUMMARY_REPOSITORY


def get_review_summarizer() -> ReviewSummarizer:
    """Provide the deterministic mock summarizer (no external AI)."""
    return DeterministicMockReviewSummarizer()


def get_ai_provider_registry() -> AIProviderRegistry:
    """Build the AI review provider registry from settings (no live HTTP by default)."""
    live = settings.ai_external_calls_enabled
    enabled = settings.ai_review_enabled
    transport = DisabledTransport()
    providers = [
        OpenAIReviewProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            transport=transport,
            live_http_enabled=live,
            ai_review_enabled=enabled,
        ),
        ClaudeReviewProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            transport=transport,
            live_http_enabled=live,
            ai_review_enabled=enabled,
        ),
        GeminiReviewProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            transport=transport,
            live_http_enabled=live,
            ai_review_enabled=enabled,
        ),
        DeterministicReviewProvider(DeterministicMockReviewSummarizer()),
    ]
    return AIProviderRegistry(providers, fallback_order=settings.ai_fallback_order)


def get_multi_model_review_orchestrator(
    registry: AIProviderRegistry = Depends(get_ai_provider_registry),
) -> MultiModelReviewOrchestrator:
    """Provide the multi-model review orchestrator."""
    return MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=settings.ai_review_enabled,
        configured_mode=settings.ai_review_mode,
        allow_client_mode=settings.ai_review_allow_client_mode,
        primary_provider=settings.ai_primary_provider,
        secondary_provider=settings.ai_secondary_provider,
        max_estimated_cost=settings.ai_max_estimated_cost_per_request,
    )


def get_review_summary_service(
    repository: ReviewSummaryRepository = Depends(get_review_summary_repository),
    summarizer: ReviewSummarizer = Depends(get_review_summarizer),
    review_service: ReviewService = Depends(get_review_service),
    orchestrator: MultiModelReviewOrchestrator = Depends(get_multi_model_review_orchestrator),
) -> ReviewSummaryService:
    """Provide the AI Review Summary orchestration service."""
    global _REVIEW_SUMMARY_SERVICE
    if _REVIEW_SUMMARY_SERVICE is None:
        _REVIEW_SUMMARY_SERVICE = ReviewSummaryService(
            repository,
            summarizer,
            review_service,
            orchestrator=orchestrator,
            max_review_input=settings.ai_max_review_input,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        )
        return _REVIEW_SUMMARY_SERVICE
    _REVIEW_SUMMARY_SERVICE._summarizer = summarizer  # noqa: SLF001
    _REVIEW_SUMMARY_SERVICE._review_service = review_service  # noqa: SLF001
    _REVIEW_SUMMARY_SERVICE._orchestrator = orchestrator  # noqa: SLF001
    return _REVIEW_SUMMARY_SERVICE


def get_shopping_conversation_repository() -> ConversationRepository:
    """Provide the process-scoped in-memory shopping conversation repository."""
    return _MEMORY_SHOPPING_CONVERSATION_REPOSITORY


def get_shopping_decision_snapshot_repository() -> DecisionSnapshotRepository:
    """Provide the process-scoped in-memory canonical decision snapshot store."""
    return _MEMORY_SHOPPING_DECISION_SNAPSHOT_REPOSITORY


def get_shopping_explanation_registry() -> ShoppingExplanationRegistry:
    """Build shopping explanation providers from settings (no live HTTP by default)."""
    live = settings.ai_shopping_external_calls_enabled
    enabled = settings.ai_shopping_enabled
    transport = DisabledTransport()
    providers = [
        OpenAIShoppingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        ClaudeShoppingProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        GeminiShoppingProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        DeterministicShoppingProviderAdapter(),
    ]
    return ShoppingExplanationRegistry(
        providers,
        fallback_order=settings.ai_fallback_order,
    )


def get_shopping_assistant_orchestrator(
    registry: ShoppingExplanationRegistry = Depends(get_shopping_explanation_registry),
) -> ShoppingAssistantOrchestrator:
    """Provide the shopping assistant multi-model orchestrator."""
    return ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=settings.ai_shopping_enabled,
        configured_mode=settings.ai_shopping_mode,
        allow_client_mode=settings.ai_shopping_allow_client_mode,
        primary_provider=settings.ai_primary_provider,
        secondary_provider=settings.ai_secondary_provider,
        max_estimated_cost=settings.ai_max_estimated_cost_per_request,
    )


def get_community_registry() -> CommunityRegistry:
    """Build pluggable community connector registry (fixtures / mock by default)."""
    use_fixtures = settings.community_use_fixtures
    transport = MockCommunityTransport()
    providers = [
        RedditCommunityProvider(
            enabled=settings.community_reddit_enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures,
        ),
        YouTubeCommunityProvider(
            enabled=settings.community_youtube_enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures,
        ),
        AmazonQACommunityProvider(
            enabled=settings.community_amazon_qa_enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures,
        ),
        MarketplaceQuestionsCommunityProvider(
            enabled=settings.community_marketplace_qa_enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures,
        ),
        ManufacturerForumsCommunityProvider(
            enabled=settings.community_forums_enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures,
        ),
        DiscordCommunityProvider(
            enabled=settings.community_discord_enabled,
            use_fixtures_when_unavailable=False,
        ),
    ]
    return CommunityRegistry(providers)


def get_community_summary_registry() -> CommunitySummaryRegistry:
    """Build community AI summary providers (DisabledTransport by default)."""
    live = settings.ai_community_external_calls_enabled
    enabled = settings.ai_community_enabled
    transport = DisabledTransport()
    providers = [
        OpenAICommunityProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        ClaudeCommunityProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        GeminiCommunityProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            transport=transport,
            live_http_enabled=live,
            ai_enabled=enabled,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
        DeterministicCommunityProviderAdapter(),
    ]
    return CommunitySummaryRegistry(providers, fallback_order=settings.ai_fallback_order)


def get_community_ai_orchestrator(
    registry: CommunitySummaryRegistry = Depends(get_community_summary_registry),
) -> CommunityAIOrchestrator:
    """Provide the community multi-model AI summarizer."""
    return CommunityAIOrchestrator(
        registry,
        ai_enabled=settings.ai_community_enabled,
        configured_mode=settings.ai_community_mode,
        allow_client_mode=settings.ai_community_allow_client_mode,
        primary_provider=settings.ai_primary_provider,
        secondary_provider=settings.ai_secondary_provider,
        max_estimated_cost=settings.ai_max_estimated_cost_per_request,
    )


def get_community_orchestrator(
    registry: CommunityRegistry = Depends(get_community_registry),
    ai_orchestrator: CommunityAIOrchestrator = Depends(get_community_ai_orchestrator),
) -> CommunityOrchestrator:
    """Provide the Community Intelligence end-to-end orchestrator."""
    return CommunityOrchestrator(registry, ai_orchestrator=ai_orchestrator)


def get_community_intelligence_service(
    orchestrator: CommunityOrchestrator = Depends(get_community_orchestrator),
) -> CommunityIntelligenceService:
    """Provide the Community Intelligence application service."""
    global _COMMUNITY_INTELLIGENCE_SERVICE
    if _COMMUNITY_INTELLIGENCE_SERVICE is None:
        _COMMUNITY_INTELLIGENCE_SERVICE = CommunityIntelligenceService(orchestrator)
        return _COMMUNITY_INTELLIGENCE_SERVICE
    _COMMUNITY_INTELLIGENCE_SERVICE._orchestrator = orchestrator  # noqa: SLF001
    return _COMMUNITY_INTELLIGENCE_SERVICE


def get_knowledge_graph_repository():
    """Provide the process-scoped in-memory knowledge graph repository."""
    global _KNOWLEDGE_GRAPH_REPOSITORY
    if _KNOWLEDGE_GRAPH_REPOSITORY is None:
        from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository

        _KNOWLEDGE_GRAPH_REPOSITORY = InMemoryKnowledgeGraphRepository(
            schema_version=settings.knowledge_graph_snapshot_schema_version,
        )
    return _KNOWLEDGE_GRAPH_REPOSITORY


def get_knowledge_graph_engine(
    repository=Depends(get_knowledge_graph_repository),
):
    """Provide the Knowledge Graph engine with server-enforced limits."""
    from app.domain.entities.knowledge_graph import GraphLimits
    from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine

    return KnowledgeGraphEngine(
        repository,
        limits=GraphLimits(
            max_depth=settings.knowledge_graph_max_depth,
            max_nodes=settings.knowledge_graph_max_nodes,
            max_edges=settings.knowledge_graph_max_edges,
            max_paths=settings.knowledge_graph_max_paths,
            min_confidence=settings.knowledge_graph_min_confidence,
        ),
    )


def get_knowledge_graph_service(
    engine=Depends(get_knowledge_graph_engine),
    community_service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> KnowledgeGraphService:
    """Provide the Knowledge Graph application service."""
    global _KNOWLEDGE_GRAPH_SERVICE
    from app.intelligence.knowledge_graph.adapters import CommunityEvidenceAdapter
    from app.intelligence.knowledge_graph.aggregator import KnowledgeGraphAggregator

    community = community_service if settings.community_enabled else None
    aggregator = KnowledgeGraphAggregator(
        engine,
        community_adapter=CommunityEvidenceAdapter(community),
    )
    if _KNOWLEDGE_GRAPH_SERVICE is None:
        _KNOWLEDGE_GRAPH_SERVICE = KnowledgeGraphService(
            engine,
            aggregator=aggregator,
            enabled=settings.knowledge_graph_enabled,
        )
        return _KNOWLEDGE_GRAPH_SERVICE
    _KNOWLEDGE_GRAPH_SERVICE._engine = engine  # noqa: SLF001
    _KNOWLEDGE_GRAPH_SERVICE._aggregator = aggregator  # noqa: SLF001
    _KNOWLEDGE_GRAPH_SERVICE._enabled = settings.knowledge_graph_enabled  # noqa: SLF001
    return _KNOWLEDGE_GRAPH_SERVICE


def get_personal_profile_repository():
    """Provide the process-scoped fixture profile repository."""
    global _PERSONAL_PROFILE_REPOSITORY
    if _PERSONAL_PROFILE_REPOSITORY is None:
        from app.intelligence.personal.memory import InMemoryCustomerProfileRepository

        _PERSONAL_PROFILE_REPOSITORY = InMemoryCustomerProfileRepository(
            default_profile_id=settings.personal_agent_default_profile_id,
        )
    return _PERSONAL_PROFILE_REPOSITORY


def get_personal_agent_service(
    community_service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
    knowledge_graph_service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> PersonalAgentService:
    """Provide the Personal AI Shopping Agent application service."""
    global _PERSONAL_AGENT_SERVICE
    from app.intelligence.personal.profile_manager import ProfileManager

    community = community_service if settings.community_enabled else None
    graph = knowledge_graph_service if settings.knowledge_graph_enabled else None
    repository = get_personal_profile_repository()
    if _PERSONAL_AGENT_SERVICE is None:
        _PERSONAL_AGENT_SERVICE = PersonalAgentService(
            profile_manager=ProfileManager(repository),
            enabled=settings.personal_agent_enabled,
            community_service=community,
            knowledge_graph_service=graph,
        )
        return _PERSONAL_AGENT_SERVICE
    _PERSONAL_AGENT_SERVICE._enabled = settings.personal_agent_enabled  # noqa: SLF001
    _PERSONAL_AGENT_SERVICE._community = community  # noqa: SLF001
    _PERSONAL_AGENT_SERVICE._knowledge_graph = graph  # noqa: SLF001
    return _PERSONAL_AGENT_SERVICE


def get_user_platform_store():
    """Provide User Platform store (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _USER_PLATFORM_STORE, _SQL_USER_PLATFORM_STORE
    if resolve_backend("user_platform") == "sqlalchemy":
        if _SQL_USER_PLATFORM_STORE is None:
            from app.infrastructure.database.repositories.user_platform_repository import (
                SqlAlchemyUserPlatformStore,
            )
            from app.user.fixtures import seed_demo_users

            _SQL_USER_PLATFORM_STORE = SqlAlchemyUserPlatformStore()
            if settings.seed_demo_data and not settings.is_production:
                seed_demo_users(_SQL_USER_PLATFORM_STORE)
        return _SQL_USER_PLATFORM_STORE
    if _USER_PLATFORM_STORE is None:
        from app.user.fixtures import seed_demo_users
        from app.user.memory import InMemoryUserPlatformStore

        _USER_PLATFORM_STORE = InMemoryUserPlatformStore()
        # In-memory adapter is the explicit demo path: seed unless production.
        if settings.seed_demo_data or not settings.is_production:
            seed_demo_users(_USER_PLATFORM_STORE)
    return _USER_PLATFORM_STORE


def get_user_platform_service() -> UserPlatformService:
    """Provide the User Platform application facade (auth, profile, saved items)."""
    global _USER_PLATFORM_SERVICE
    if _USER_PLATFORM_SERVICE is None:
        from app.auth.security import AuditLogger
        from app.auth.service import AuthService
        from app.profile.service import ProfileService
        from app.session.service import SessionService

        store = get_user_platform_store()
        audit = AuditLogger(store.audit)
        auth = AuthService(
            users=store.users,
            sessions=store.sessions,
            profiles=store.profiles,
            password_resets=store.password_resets,
            email_verifications=store.email_verifications,
            audit=audit,
            enabled=settings.user_platform_enabled,
        )
        profiles = ProfileService(users=store.users, profiles=store.profiles)
        sessions = SessionService(sessions=store.sessions, auth=auth)
        _USER_PLATFORM_SERVICE = UserPlatformService(
            auth=auth,
            profiles=profiles,
            sessions=sessions,
            saved=store.saved,
            audit=audit,
            enabled=settings.user_platform_enabled,
        )
    return _USER_PLATFORM_SERVICE


_EARLY_ACCESS_MEMORY_REPO = None


def get_early_access_repository():
    """Provide the Early Access repository (SQLAlchemy operational store or memory)."""
    global _EARLY_ACCESS_MEMORY_REPO
    from app.early_access.memory import InMemoryEarlyAccessRepository
    from app.infrastructure.database.repositories.early_access_repository import (
        SqlAlchemyEarlyAccessRepository,
    )
    from app.infrastructure.persistence.binding import resolve_persistence_default

    if resolve_persistence_default() == "sqlalchemy":
        return SqlAlchemyEarlyAccessRepository()
    if _EARLY_ACCESS_MEMORY_REPO is None:
        _EARLY_ACCESS_MEMORY_REPO = InMemoryEarlyAccessRepository()
    return _EARLY_ACCESS_MEMORY_REPO


def get_early_access_service():
    """Provide the Early Access registration service."""
    global _EARLY_ACCESS_SERVICE
    if _EARLY_ACCESS_SERVICE is None:
        from app.services.early_access_service import EarlyAccessService

        _EARLY_ACCESS_SERVICE = EarlyAccessService(get_early_access_repository())
    return _EARLY_ACCESS_SERVICE


def get_user_dashboard_service(
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    alert_rule_service: AlertRuleService = Depends(get_alert_rule_service),
    alert_repository: AlertRepository = Depends(get_alert_repository),
    alert_event_repository: AlertEventRepository = Depends(get_alert_event_repository),
    notification_center_service: NotificationCenterService = Depends(
        get_notification_center_service
    ),
    marketplace_data_service: MarketplaceDataService = Depends(get_marketplace_data_service),
    user_platform_service: UserPlatformService = Depends(get_user_platform_service),
) -> UserDashboardService:
    """Provide the User Dashboard aggregation service (Sprint 19)."""
    global _USER_DASHBOARD_SERVICE
    market_data = marketplace_data_service if settings.marketplace_data_enabled else None
    user_platform = user_platform_service if settings.user_platform_enabled else None
    if _USER_DASHBOARD_SERVICE is None:
        _USER_DASHBOARD_SERVICE = UserDashboardService(
            watchlist_service,
            alert_rule_service=alert_rule_service,
            alert_repository=alert_repository,
            alert_event_repository=alert_event_repository,
            notification_center_service=notification_center_service,
            marketplace_data_service=market_data,
            user_platform_service=user_platform,
        )
        return _USER_DASHBOARD_SERVICE

    _USER_DASHBOARD_SERVICE._watchlist_service = watchlist_service  # noqa: SLF001
    _USER_DASHBOARD_SERVICE._alert_rules = alert_rule_service  # noqa: SLF001
    _USER_DASHBOARD_SERVICE._notification_center = notification_center_service  # noqa: SLF001
    _USER_DASHBOARD_SERVICE._marketplace_data = market_data  # noqa: SLF001
    _USER_DASHBOARD_SERVICE._user_platform = user_platform  # noqa: SLF001
    return _USER_DASHBOARD_SERVICE


def get_affiliate_repository():
    """Provide Affiliate Revenue Engine store (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _SQL_AFFILIATE_REPOSITORY
    if resolve_backend("affiliate") == "sqlalchemy":
        if _SQL_AFFILIATE_REPOSITORY is None:
            from app.infrastructure.database.repositories.affiliate_repository import (
                SqlAlchemyAffiliateRepository,
            )

            seed = settings.seed_demo_data and not settings.is_production
            _SQL_AFFILIATE_REPOSITORY = SqlAlchemyAffiliateRepository(seed=seed)
        return _SQL_AFFILIATE_REPOSITORY
    return _MEMORY_AFFILIATE_REPOSITORY


def get_affiliate_merchant_service(
    repository=Depends(get_affiliate_repository),
) -> AffiliateMerchantService:
    """Provide the Affiliate Merchant registry service (Sprint 20)."""
    global _AFFILIATE_MERCHANT_SERVICE
    if _AFFILIATE_MERCHANT_SERVICE is None:
        _AFFILIATE_MERCHANT_SERVICE = AffiliateMerchantService(repository)
    return _AFFILIATE_MERCHANT_SERVICE


def get_affiliate_link_service(
    repository=Depends(get_affiliate_repository),
    merchant_service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateLinkService:
    """Provide the Affiliate Link generation service (Sprint 20)."""
    global _AFFILIATE_LINK_SERVICE
    if _AFFILIATE_LINK_SERVICE is None:
        _AFFILIATE_LINK_SERVICE = AffiliateLinkService(
            repository,
            repository,
            merchant_service=merchant_service,
        )
        return _AFFILIATE_LINK_SERVICE
    _AFFILIATE_LINK_SERVICE._merchant_service = merchant_service  # noqa: SLF001
    return _AFFILIATE_LINK_SERVICE


def get_affiliate_tracking_service(
    repository=Depends(get_affiliate_repository),
) -> AffiliateTrackingService:
    """Provide the Affiliate click tracking / attribution service (Sprint 20)."""
    global _AFFILIATE_TRACKING_SERVICE
    if _AFFILIATE_TRACKING_SERVICE is None:
        _AFFILIATE_TRACKING_SERVICE = AffiliateTrackingService(
            repository,
            link_repository=repository,
            merchant_repository=repository,
            attribution_repository=repository,
        )
    return _AFFILIATE_TRACKING_SERVICE


def get_affiliate_reporting_service(
    repository=Depends(get_affiliate_repository),
) -> AffiliateReportingService:
    """Provide the Affiliate revenue reporting service (Sprint 20)."""
    global _AFFILIATE_REPORTING_SERVICE
    if _AFFILIATE_REPORTING_SERVICE is None:
        _AFFILIATE_REPORTING_SERVICE = AffiliateReportingService(
            repository, impression_store=repository
        )
    return _AFFILIATE_REPORTING_SERVICE


def get_affiliate_disclosure_service(
    repository=Depends(get_affiliate_repository),
) -> AffiliateDisclosureService:
    """Provide the Affiliate disclosure service (Sprint 20)."""
    global _AFFILIATE_DISCLOSURE_SERVICE
    if _AFFILIATE_DISCLOSURE_SERVICE is None:
        _AFFILIATE_DISCLOSURE_SERVICE = AffiliateDisclosureService(repository)
    return _AFFILIATE_DISCLOSURE_SERVICE


def get_merchant_repository():
    """Provide Merchant Platform store (memory or sqlalchemy per config)."""
    from app.infrastructure.persistence.binding import resolve_backend

    global _SQL_MERCHANT_REPOSITORY
    if resolve_backend("merchant") == "sqlalchemy":
        if _SQL_MERCHANT_REPOSITORY is None:
            from app.infrastructure.database.repositories.merchant_repository import (
                SqlAlchemyMerchantRepository,
            )

            seed = settings.seed_demo_data and not settings.is_production
            _SQL_MERCHANT_REPOSITORY = SqlAlchemyMerchantRepository(seed=seed)
        return _SQL_MERCHANT_REPOSITORY
    return _MEMORY_MERCHANT_REPOSITORY


def get_merchant_auth_service(
    repository=Depends(get_merchant_repository),
) -> MerchantAuthService:
    """Provide merchant actor resolution (Sprint 21)."""
    global _MERCHANT_AUTH_SERVICE
    if _MERCHANT_AUTH_SERVICE is None:
        _MERCHANT_AUTH_SERVICE = MerchantAuthService(repository, repository)
    return _MERCHANT_AUTH_SERVICE


def get_merchant_organization_service(
    repository=Depends(get_merchant_repository),
) -> MerchantOrganizationService:
    """Provide merchant organization management (Sprint 21)."""
    global _MERCHANT_ORGANIZATION_SERVICE
    if _MERCHANT_ORGANIZATION_SERVICE is None:
        _MERCHANT_ORGANIZATION_SERVICE = MerchantOrganizationService(
            repository, repository, repository
        )
    return _MERCHANT_ORGANIZATION_SERVICE


def get_merchant_membership_service(
    repository=Depends(get_merchant_repository),
) -> MerchantMembershipService:
    """Provide merchant membership / invitation management (Sprint 21)."""
    global _MERCHANT_MEMBERSHIP_SERVICE
    if _MERCHANT_MEMBERSHIP_SERVICE is None:
        _MERCHANT_MEMBERSHIP_SERVICE = MerchantMembershipService(repository, repository, repository)
    return _MERCHANT_MEMBERSHIP_SERVICE


def get_merchant_product_service(
    repository=Depends(get_merchant_repository),
) -> MerchantProductService:
    """Provide merchant product submission service (Sprint 21)."""
    global _MERCHANT_PRODUCT_SERVICE
    if _MERCHANT_PRODUCT_SERVICE is None:
        _MERCHANT_PRODUCT_SERVICE = MerchantProductService(
            repository, repository, matcher=repository.matcher
        )
    return _MERCHANT_PRODUCT_SERVICE


def get_merchant_offer_service(
    repository=Depends(get_merchant_repository),
) -> MerchantOfferService:
    """Provide merchant offer submission service (Sprint 21)."""
    global _MERCHANT_OFFER_SERVICE
    if _MERCHANT_OFFER_SERVICE is None:
        _MERCHANT_OFFER_SERVICE = MerchantOfferService(repository, repository)
    return _MERCHANT_OFFER_SERVICE


def get_merchant_promotion_service(
    repository=Depends(get_merchant_repository),
) -> MerchantPromotionService:
    """Provide merchant promotion management (Sprint 21)."""
    global _MERCHANT_PROMOTION_SERVICE
    if _MERCHANT_PROMOTION_SERVICE is None:
        _MERCHANT_PROMOTION_SERVICE = MerchantPromotionService(repository, repository)
    return _MERCHANT_PROMOTION_SERVICE


def get_merchant_campaign_service(
    repository=Depends(get_merchant_repository),
) -> MerchantCampaignService:
    """Provide sponsored campaign draft management (Sprint 21)."""
    global _MERCHANT_CAMPAIGN_SERVICE
    if _MERCHANT_CAMPAIGN_SERVICE is None:
        _MERCHANT_CAMPAIGN_SERVICE = MerchantCampaignService(repository, repository)
    return _MERCHANT_CAMPAIGN_SERVICE


def get_merchant_analytics_service(
    repository=Depends(get_merchant_repository),
    affiliate_repo=Depends(get_affiliate_repository),
) -> MerchantAnalyticsService:
    """Provide merchant analytics + ranking explanations (Sprint 21)."""
    global _MERCHANT_ANALYTICS_SERVICE
    if _MERCHANT_ANALYTICS_SERVICE is None:
        _MERCHANT_ANALYTICS_SERVICE = MerchantAnalyticsService(
            repository,
            repository,
            repository,
            repository,
            repository,
            affiliate_click_lister=affiliate_repo.list_clicks,
        )
        return _MERCHANT_ANALYTICS_SERVICE
    _MERCHANT_ANALYTICS_SERVICE._affiliate_click_lister = (  # noqa: SLF001
        affiliate_repo.list_clicks
    )
    return _MERCHANT_ANALYTICS_SERVICE


def get_merchant_admin_service(
    repository=Depends(get_merchant_repository),
) -> MerchantAdminService:
    """Provide internal admin review workflows (Sprint 21)."""
    global _MERCHANT_ADMIN_SERVICE
    if _MERCHANT_ADMIN_SERVICE is None:
        _MERCHANT_ADMIN_SERVICE = MerchantAdminService(
            repository, repository, repository, repository
        )
    return _MERCHANT_ADMIN_SERVICE


def get_shopping_assistant_service(
    conversations: ConversationRepository = Depends(get_shopping_conversation_repository),
    snapshots: DecisionSnapshotRepository = Depends(get_shopping_decision_snapshot_repository),
    orchestrator: ShoppingAssistantOrchestrator = Depends(get_shopping_assistant_orchestrator),
    community_service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
    knowledge_graph_service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    personal_agent_service: PersonalAgentService = Depends(get_personal_agent_service),
    user_platform_service: UserPlatformService = Depends(get_user_platform_service),
    marketplace_data_service: MarketplaceDataService = Depends(get_marketplace_data_service),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    alert_rule_service: AlertRuleService = Depends(get_alert_rule_service),
    notification_center_service: NotificationCenterService = Depends(
        get_notification_center_service
    ),
    alert_evaluation_service: AlertEvaluationService = Depends(get_alert_evaluation_service),
    affiliate_link_service: AffiliateLinkService = Depends(get_affiliate_link_service),
) -> ShoppingAssistantService:
    """Provide the AI Shopping Assistant orchestration service."""
    global _SHOPPING_ASSISTANT_SERVICE
    community = community_service if settings.community_enabled else None
    graph = knowledge_graph_service if settings.knowledge_graph_enabled else None
    personal = personal_agent_service if settings.personal_agent_enabled else None
    user_platform = user_platform_service if settings.user_platform_enabled else None
    marketplace_data = marketplace_data_service if settings.marketplace_data_enabled else None
    watchlists = watchlist_service if settings.watchlists_alerts_enabled else None
    alert_rules = alert_rule_service if settings.watchlists_alerts_enabled else None
    notification_center = (
        notification_center_service if settings.watchlists_alerts_enabled else None
    )
    alert_evaluation = alert_evaluation_service if settings.watchlists_alerts_enabled else None
    affiliate_links = affiliate_link_service if settings.affiliate_enabled else None
    if _SHOPPING_ASSISTANT_SERVICE is None:
        _SHOPPING_ASSISTANT_SERVICE = ShoppingAssistantService(
            orchestrator=orchestrator,
            conversation_repository=conversations,
            snapshot_repository=snapshots,
            max_query_length=settings.ai_shopping_max_query_length,
            community_service=community,
            knowledge_graph_service=graph,
            personal_agent_service=personal,
            user_platform_service=user_platform,
            marketplace_data_service=marketplace_data,
            watchlist_service=watchlists,
            alert_rule_service=alert_rules,
            notification_center_service=notification_center,
            alert_evaluation_service=alert_evaluation,
            affiliate_link_service=affiliate_links,
        )
        return _SHOPPING_ASSISTANT_SERVICE
    _SHOPPING_ASSISTANT_SERVICE._orchestrator = orchestrator  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._conversations = conversations  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._evidence_answers._snapshots = snapshots  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._evidence_answers._conversations = conversations  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._community = community  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._knowledge_graph = graph  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._personal_agent = personal  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._user_platform = user_platform  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._marketplace_data = marketplace_data  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._watchlist_service = watchlists  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._alert_rule_service = alert_rules  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._notification_center = notification_center  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._alert_evaluation_service = alert_evaluation  # noqa: SLF001
    _SHOPPING_ASSISTANT_SERVICE._affiliate_link_service = affiliate_links  # noqa: SLF001
    return _SHOPPING_ASSISTANT_SERVICE


# ---------------------------------------------------------------------------
# Sprint 22 — Launch readiness providers
# ---------------------------------------------------------------------------


def get_rate_limiter() -> ConfigurableRateLimiter:
    """Provide the process-scoped HTTP rate limiter."""
    return _RATE_LIMITER


def get_performance_cache() -> TtlCache:
    """Provide the process-scoped performance TTL cache."""
    return _PERFORMANCE_CACHE


def get_launch_store() -> InMemoryLaunchStore:
    return _LAUNCH_STORE


def get_feature_flag_registry() -> FeatureFlagRegistry:
    return get_feature_flags()


def get_launch_health_service() -> LaunchHealthService:
    global _LAUNCH_HEALTH_SERVICE
    if _LAUNCH_HEALTH_SERVICE is None:
        _LAUNCH_HEALTH_SERVICE = LaunchHealthService(cache=_PERFORMANCE_CACHE)
    return _LAUNCH_HEALTH_SERVICE


def get_launch_performance_service() -> LaunchPerformanceService:
    global _LAUNCH_PERFORMANCE_SERVICE
    if _LAUNCH_PERFORMANCE_SERVICE is None:
        _LAUNCH_PERFORMANCE_SERVICE = LaunchPerformanceService(_PERFORMANCE_CACHE)
    return _LAUNCH_PERFORMANCE_SERVICE


def get_launch_demo_service() -> LaunchDemoService:
    global _LAUNCH_DEMO_SERVICE
    if _LAUNCH_DEMO_SERVICE is None:
        _LAUNCH_DEMO_SERVICE = LaunchDemoService(_DEMO_LAUNCHER_STATE)
    return _LAUNCH_DEMO_SERVICE


def get_launch_config_service() -> LaunchConfigService:
    global _LAUNCH_CONFIG_SERVICE
    if _LAUNCH_CONFIG_SERVICE is None:
        _LAUNCH_CONFIG_SERVICE = LaunchConfigService(_LAUNCH_STORE)
    return _LAUNCH_CONFIG_SERVICE


def get_launch_dashboard_service() -> LaunchDashboardService:
    """Aggregate demo metrics for the launch admin dashboard."""
    global _LAUNCH_DASHBOARD_SERVICE
    if _LAUNCH_DASHBOARD_SERVICE is None:

        def _users() -> int:
            store = get_user_platform_store()
            return len(store.users.list_users())

        def _watchlists() -> int:
            return len(_MEMORY_WATCHLIST_REPOSITORY.list_watchlists())

        def _merchants() -> int:
            return len(get_merchant_repository().list_organizations())

        def _affiliate_clicks() -> int:
            return len(get_affiliate_repository().list_clicks(limit=10_000))

        def _alerts() -> int:
            return len(get_alert_rule_repository().list_rules())

        def _notifications() -> int:
            repo = get_notification_center_repository()
            if hasattr(repo, "_notifications"):
                return len(repo._notifications)  # noqa: SLF001
            # SQLAlchemy adapter: approximate via empty-user listing is wrong; use ops count if present
            try:
                from app.infrastructure.persistence.operational_store import OperationalStore
                from app.infrastructure.persistence.session import sync_session
                from app.infrastructure.persistence.stores import NC_NOTIFICATIONS

                with sync_session() as session:
                    return OperationalStore(session).count(NC_NOTIFICATIONS)
            except Exception:
                return 0

        def _products() -> int:
            return len(get_merchant_repository().list_product_submissions(limit=10_000))

        def _offers() -> int:
            return len(get_merchant_repository().list_offer_submissions(limit=10_000))

        def _campaigns() -> int:
            return len(get_merchant_repository().list_campaigns(limit=10_000))

        _LAUNCH_DASHBOARD_SERVICE = LaunchDashboardService(
            health_service=get_launch_health_service(),
            feature_flags=get_feature_flag_registry(),
            store=_LAUNCH_STORE,
            cache=_PERFORMANCE_CACHE,
            user_counter=_users,
            watchlist_counter=_watchlists,
            merchant_counter=_merchants,
            affiliate_click_counter=_affiliate_clicks,
            alert_counter=_alerts,
            notification_counter=_notifications,
            product_counter=_products,
            offer_counter=_offers,
            campaign_counter=_campaigns,
        )
    return _LAUNCH_DASHBOARD_SERVICE
