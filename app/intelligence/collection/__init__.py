"""Marketplace Collection infrastructure — Sprint 8.

Mock collectors, deterministic scheduler, retry policy, and rate limiter.
No live marketplace HTTP, LLMs, Celery, Redis, or background threads.
"""

from app.intelligence.collection.ids import make_collection_run_id
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.memory import InMemoryCollectionJobRepository
from app.intelligence.collection.rate_limiter import InMemoryMarketplaceRateLimiter
from app.intelligence.collection.retry import (
    CollectionRetryPolicy,
    RetryableCollectionError,
    RetryDecision,
)
from app.intelligence.collection.scheduler import InMemoryCollectionScheduler
from app.intelligence.collection.shopee import MockShopeeCollector

__all__ = [
    "CollectionRetryPolicy",
    "InMemoryCollectionJobRepository",
    "InMemoryCollectionScheduler",
    "InMemoryMarketplaceRateLimiter",
    "MockLazadaCollector",
    "MockShopeeCollector",
    "RetryDecision",
    "RetryableCollectionError",
    "make_collection_run_id",
]
