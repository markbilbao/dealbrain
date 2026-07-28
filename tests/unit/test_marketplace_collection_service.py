"""Unit tests for MarketplaceCollectionService orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.domain.entities.collection import CollectionStatus, CollectionTarget
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.memory import InMemoryCollectionJobRepository
from app.intelligence.collection.rate_limiter import InMemoryMarketplaceRateLimiter
from app.intelligence.collection.retry import CollectionRetryPolicy, RetryableCollectionError
from app.intelligence.collection.shopee import MockShopeeCollector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService

FIXED_NOW = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)


class FailingCollector(MarketplaceCollector):
    def __init__(self, *, marketplace_name: str = "broken") -> None:
        self._name = marketplace_name

    @property
    def marketplace_name(self) -> str:
        return self._name

    def health_check(self) -> bool:
        return True

    def collect(self, target: CollectionTarget):
        raise RetryableCollectionError("timeout", f"{self._name} timed out for {target.query}")


class MalformedListingCollector(MarketplaceCollector):
    @property
    def marketplace_name(self) -> str:
        return "malformed_source"

    def health_check(self) -> bool:
        return True

    def collect(self, target: CollectionTarget):
        from app.domain.entities.collection import (
            CollectedListing,
            CollectionResult,
            CollectionStatus,
        )

        listing = MarketplaceListing(
            marketplace="malformed_source",
            product_id="",
            title="",
            price=-1,
            currency="",
            seller="",
            rating=None,
            url="",
            availability=AvailabilityStatus.UNKNOWN,
        )
        return CollectionResult(
            run_id="malformed-run",
            marketplace=self.marketplace_name,
            query=target.query,
            target_id=None,
            started_at=FIXED_NOW,
            completed_at=FIXED_NOW,
            listing_count=1,
            successful_listing_count=1,
            failed_listing_count=0,
            listings=(
                CollectedListing(
                    listing=listing,
                    source_marketplace=self.marketplace_name,
                    collected_at=FIXED_NOW,
                ),
            ),
            status=CollectionStatus.COMPLETED,
        )


def _build_service(
    collectors: list[MarketplaceCollector] | None = None,
    *,
    rate_limiter: InMemoryMarketplaceRateLimiter | None = None,
    store: InMemoryPriceHistoryStore | None = None,
) -> tuple[MarketplaceCollectionService, InMemoryPriceHistoryStore]:
    memory = store or InMemoryPriceHistoryStore()
    price = PriceHistoryService(memory, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    counter = {"n": 0}

    def next_snapshot_id() -> UUID:
        counter["n"] += 1
        return UUID(f"aaaaaaaa-bbbb-4ccc-8ddd-{counter['n']:012d}")

    service = MarketplaceCollectionService(
        collectors
        or [
            MockShopeeCollector(clock=lambda: FIXED_NOW),
            MockLazadaCollector(clock=lambda: FIXED_NOW),
        ],
        price_history_service=price,
        product_intelligence_service=product,
        repository=InMemoryCollectionJobRepository(),
        rate_limiter=rate_limiter,
        retry_policy=CollectionRetryPolicy(max_attempts=2, base_delay_seconds=1.0),
        clock=lambda: FIXED_NOW,
        snapshot_id_factory=next_snapshot_id,
    )
    return service, memory


@pytest.mark.asyncio
async def test_successful_multi_marketplace_collection() -> None:
    service, store = _build_service()
    run = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        observed_at=FIXED_NOW,
    )
    assert run.status in {CollectionStatus.COMPLETED, CollectionStatus.PARTIALLY_COMPLETED}
    assert set(run.marketplaces_attempted) == {"shopee", "lazada"}
    assert run.collected_count >= 2
    assert run.stored_snapshot_count >= 1
    assert run.to_summary_dict()["run_id"] == run.run_id


@pytest.mark.asyncio
async def test_one_collector_failing_while_another_succeeds() -> None:
    service, _ = _build_service(
        [
            MockShopeeCollector(clock=lambda: FIXED_NOW),
            FailingCollector(marketplace_name="lazada"),
        ]
    )
    run = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        observed_at=FIXED_NOW,
    )
    assert run.status == CollectionStatus.PARTIALLY_COMPLETED
    shopee = next(r for r in run.results if r.marketplace == "shopee")
    lazada = next(r for r in run.results if r.marketplace == "lazada")
    assert shopee.status == CollectionStatus.COMPLETED
    assert lazada.status == CollectionStatus.FAILED
    assert run.stored_snapshot_count >= 1


@pytest.mark.asyncio
async def test_malformed_listing_rejection() -> None:
    service, store = _build_service([MalformedListingCollector()])
    run = await service.run_collection(
        query="anything",
        marketplaces=["malformed_source"],
        observed_at=FIXED_NOW,
    )
    assert run.stored_snapshot_count == 0
    assert run.skipped_count >= 1
    assert any("malformed" in warning.lower() for warning in run.warnings)
    assert await store.get_by_listing("") == []


@pytest.mark.asyncio
async def test_duplicate_snapshot_handling() -> None:
    service, store = _build_service()
    first = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        observed_at=FIXED_NOW,
    )
    second = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        observed_at=FIXED_NOW,
    )
    assert first.stored_snapshot_count >= 1
    assert second.stored_snapshot_count >= 1
    # Uniqueness key prevents duplicate rows for same observation.
    stored = await store.get_by_listing("1001001")
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_mixed_currency_preservation() -> None:
    class MultiCurrencyCollector(MarketplaceCollector):
        @property
        def marketplace_name(self) -> str:
            return "shopee"

        def health_check(self) -> bool:
            return True

        def collect(self, target: CollectionTarget):
            from app.domain.entities.collection import CollectedListing, CollectionResult

            listings = (
                CollectedListing(
                    listing=MarketplaceListing(
                        marketplace="shopee",
                        product_id="php-1",
                        title="Apple iPhone 17 Pro Max 256GB Black Titanium",
                        price=100.0,
                        currency="PHP",
                        seller="A",
                        rating=4.0,
                        url="https://example.com/1",
                        availability=AvailabilityStatus.IN_STOCK,
                    ),
                    source_marketplace="shopee",
                    collected_at=FIXED_NOW,
                ),
                CollectedListing(
                    listing=MarketplaceListing(
                        marketplace="shopee",
                        product_id="usd-1",
                        title="Apple iPhone 16 Pro 128GB White Titanium",
                        price=50.0,
                        currency="USD",
                        seller="B",
                        rating=4.0,
                        url="https://example.com/2",
                        availability=AvailabilityStatus.IN_STOCK,
                    ),
                    source_marketplace="shopee",
                    collected_at=FIXED_NOW,
                ),
            )
            return CollectionResult(
                run_id="multi-currency",
                marketplace="shopee",
                query=target.query,
                target_id=None,
                started_at=FIXED_NOW,
                completed_at=FIXED_NOW,
                listing_count=2,
                successful_listing_count=2,
                failed_listing_count=0,
                listings=listings,
                status=CollectionStatus.COMPLETED,
            )

    service, store = _build_service([MultiCurrencyCollector()])
    run = await service.run_collection(
        query="iPhone",
        marketplaces=["shopee"],
        observed_at=FIXED_NOW,
    )
    assert run.stored_snapshot_count == 2
    php = await store.get_by_listing("php-1")
    usd = await store.get_by_listing("usd-1")
    assert php[0].currency == "PHP"
    assert usd[0].currency == "USD"
    assert php[0].item_price == 100.0
    assert usd[0].item_price == 50.0


@pytest.mark.asyncio
async def test_retry_exhaustion_isolates_failure() -> None:
    service, _ = _build_service([FailingCollector(marketplace_name="shopee")])
    run = await service.run_collection(
        query="iPhone",
        marketplaces=["shopee"],
        observed_at=FIXED_NOW,
    )
    assert run.status == CollectionStatus.FAILED
    assert run.results[0].status == CollectionStatus.FAILED
    assert run.results[0].errors[0].code == "timeout"


@pytest.mark.asyncio
async def test_deterministic_identical_runs() -> None:
    service, _ = _build_service()
    first = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        observed_at=FIXED_NOW,
        run_id="fixed-run-id",
    )
    second = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        observed_at=FIXED_NOW,
        run_id="fixed-run-id",
    )
    assert first.run_id == second.run_id == "fixed-run-id"
    assert first.collected_count == second.collected_count
    assert first.to_summary_dict()["collected_count"] == second.to_summary_dict()["collected_count"]


@pytest.mark.asyncio
async def test_job_crud() -> None:
    service, _ = _build_service()
    job = service.create_job(
        query="iPhone",
        marketplaces=["shopee"],
        interval_seconds=60,
        created_at=FIXED_NOW,
        job_id="job-1",
    )
    assert job.job_id == "job-1"
    assert len(service.list_jobs()) == 1
    service.delete_job("job-1")
    assert service.list_jobs() == []
