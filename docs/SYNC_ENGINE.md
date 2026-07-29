"""Marketplace Sync Engine — Sprint 18.

Status: implemented (in-process, no external scheduler)
Date: 2026-07-29

Scope
-----
Full and incremental synchronization of connector offers into normalized
storage with checkpoints, advisory retries, rate-limit handling, conflict
reporting, and dead-letter retention. Sync is triggered explicitly via API /
service calls — there is **no** Celery, cron, Redis, or APScheduler.

Architecture
------------
```
POST /api/v1/marketplaces/sync
  → MarketplaceDataService.trigger_sync
      → MarketplaceSyncEngine.run
          → rate-limit check
          → fetch_offers (optional checkpoint for incremental)
          → SyncRetryPolicy (advisory delays — no sleeping)
          → normalize + match + persist offer/price/inventory
          → save checkpoint / health / conflicts / dead letters
```

Modes
-----
- ``full`` — ignore prior checkpoint; fetch from the start
- ``incremental`` — continue from stored ``SyncCheckpoint.cursor`` when the
  connector supports ``CONTINUE_FROM_CHECKPOINT`` (mock-live does)

Job lifecycle
-------------
``pending`` → ``running`` → ``completed`` | ``partially_completed`` | ``failed``
| ``cancelled``

Idempotency: ``idempotency_key`` returns the prior ``SyncJob`` unchanged.

Retries and rate limits
-----------------------
``SyncRetryPolicy``:

- max attempts (default 3)
- retryable codes: ``rate_limited``, ``timeout``, ``transient``,
  ``simulated_transient_failure``
- exponential advisory delay ``base * 2^(attempt-1)``, capped
- **no sleeping** in domain or tests

Partial failures
----------------
Per-record normalize/write failures increment ``records_failed``, write a
``DeadLetterRecord``, and continue. Mixed success yields
``partially_completed``.

Matching conflicts
------------------
Ambiguous or low-confidence product matches produce ``SyncConflict`` review
items; uncertain products are never silently merged.

Limitations
-----------
- In-memory jobs and checkpoints only
- No distributed locks or background workers
- Mock-live rate limits are simulated
- Future official connectors must supply their own fetch/checkpoint semantics

Extension guide for official connectors
---------------------------------------
1. Implement fetch + checkpoint continuation on ``MarketplaceDataConnector``.
2. Report honest rate-limit state via ``report_rate_limit``.
3. Register retryable error codes for the provider.
4. Cover full/incremental, retry, rate-limit, and partial-failure tests.
5. Keep auth/secrets outside the sync engine; never scrape.
"""
