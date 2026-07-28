"""Marketplace Collection Infrastructure — Sprint 8.

Status: implemented (mock collectors only)
Date: 2026-07-28

Scope
-----
Deterministic infrastructure to collect marketplace listings on a schedule and
store Price History snapshots. This sprint does **not** scrape live Shopee,
Lazada, Amazon, or other marketplaces, and does not call LLMs.

Architecture
------------
```
API (/api/v1/collections)
  → MarketplaceCollectionService
      → MarketplaceCollector (mock Shopee / Lazada)
      → MarketplaceRateLimiter (in-memory)
      → CollectionRetryPolicy (no sleeping)
      → PriceHistoryService.record_listing_snapshot
      → CollectionJobRepository (in-memory)
  → CollectionScheduler.run_due_jobs (in-memory, no threads)
```

Domain entities
---------------
- ``CollectionJob`` — scheduled interval definition
- ``CollectionRun`` — multi-marketplace orchestration outcome
- ``CollectionTarget`` — query / marketplace / scenario for one collector
- ``CollectionResult`` — per-marketplace outcome with counts and errors
- ``CollectedListing`` — normalized listing wrapper
- ``CollectionFailure`` — explainable failure with retryable flag
- ``CollectionStatus`` — pending | running | completed | partially_completed | failed | cancelled

Identifiers and timestamps are injected. Core business logic never generates
random UUIDs; ``make_collection_run_id`` / ``make_job_id`` are hash-based.

Collector interface
-------------------
``MarketplaceCollector`` requires:

- ``marketplace_name``
- ``collect(target) -> CollectionResult``
- ``health_check() -> bool``

Mock collectors reuse Sprint 4 fixture payloads and normalize through the
existing ``ShopeeConnector`` / ``LazadaConnector`` helpers. Supported scenarios:

- ``success`` (default)
- ``empty``
- ``partial_failure``
- ``total_failure``
- ``unavailable``
- ``malformed``
- ``duplicate``

Scheduler model
---------------
``CollectionScheduler`` operations: ``register_job``, ``remove_job``,
``list_jobs``, ``run_due_jobs``.

``InMemoryCollectionScheduler``:

- accepts an injected clock
- executes **only** when ``run_due_jobs`` is called
- supports interval definitions via ``interval_seconds``
- prevents the same job from running concurrently
- records ``last_run_at`` and advances ``next_run_at``
- introduces **no** background threads, Celery, Redis, APScheduler, or cron

Retry policy
------------
``CollectionRetryPolicy``:

- maximum attempts
- retryable vs non-retryable error codes
- exponential delay calculation (``base * 2^(attempt-1)``, capped)
- **no sleeping** in domain or tests — delays are advisory only

Rate limiter
------------
``MarketplaceRateLimiter`` + ``InMemoryMarketplaceRateLimiter``:

- allow / reject decisions
- retry-after calculation
- no real waiting or network throttling

Snapshot integration
--------------------
Valid collected listings are forwarded to ``PriceHistoryService``:

- preserve marketplace and listing identifiers
- preserve currency (no silent FX conversion)
- preserve item price, shipping, availability, observation timestamp
- calculate ``total_cost = item_price + shipping_cost`` consistently
- duplicate uniqueness key
  ``(canonical_product_id, marketplace, listing_id, observed_at)``
  is handled safely by the existing Price History store

Malformed listings are rejected before storage. One marketplace failure does
not fail other marketplaces.

Mock-only limitations
---------------------
- Collectors return canned fixtures only
- No live marketplace HTTP clients
- No production scheduling persistence (SQLAlchemy placeholder exists)
- Demo rate limits are generous for interactive use

Adding a future real marketplace adapter
----------------------------------------
1. Implement ``MarketplaceCollector`` (and optionally ``MarketplaceConnector``).
2. Normalize into ``MarketplaceListing``.
3. Register the collector in ``get_marketplace_collectors()``.
4. Wire rate limits and retry codes for that marketplace.
5. Keep live HTTP, auth secrets, and legal controls outside the domain layer.
6. Never invent prices; only store observed values.

Operational and legal considerations
------------------------------------
Live marketplace integrations must respect marketplace terms of service, robots
rules, official partner APIs where available, rate limits, and data retention
obligations. Prefer official APIs over scraping. Log structured summaries only —
never secrets or full raw marketplace payloads. Obtain legal review before
enabling production collection against third-party marketplaces.

Observability
-------------
Each run emits a structured summary including ``run_id``, marketplaces
attempted/completed, duration, collected count, stored snapshot count, skipped
count, and failure count via ``CollectionRun.to_summary_dict()``.
"""
