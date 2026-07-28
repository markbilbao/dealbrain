"""Collection Operations & Monitoring — Sprint 9.

Status: implemented (mock collectors only)
Date: 2026-07-28

Scope
-----
Operational control layer for the Sprint 8 Marketplace Collection
Infrastructure. Jobs are observable, controllable, and safe to operate.
This sprint does **not** scrape live marketplaces, call LLMs, or start
background workers that sleep.

Architecture
------------
```
API (/api/v1/collection-operations)
  → CollectionOperationsService
      → MarketplaceCollectionService (Sprint 8 orchestration)
      → CollectionJobRepository / CollectionRunRepository (in-memory)
      → CollectionScheduler.run_due_jobs (in-memory, no threads)
      → PriceHistoryStore (readiness + snapshot totals via run history)
      → Mock MarketplaceCollector health checks
```

Job lifecycle
-------------
1. **Create** — name, query, marketplaces, interval_minutes, enabled.
2. **Active** — enabled and not paused; eligible for due-job execution.
3. **Pause** — remains enabled but skipped by ``run-due`` and blocked from
   manual run unless ``override=true``.
4. **Resume** — clears paused; job becomes active again.
5. **Disable** — ``enabled=false``; cannot run without override.
6. **Update** — frequency, query, marketplaces, name, enabled flag.
7. **Delete** — removes job from repository and scheduler.
8. **Manual run** — executes immediately with optional idempotency key.
9. **Scheduled run** — occurs only when ``POST /run-due`` (or a future
   worker calling the same method) finds the job due.

Status definitions
------------------
Job status (derived):

- ``active`` — enabled, not paused, not running
- ``paused`` — paused flag set
- ``disabled`` — enabled=false
- ``running`` — currently executing

Run status (from Sprint 8):

- ``pending`` / ``running`` / ``completed`` / ``partially_completed`` /
  ``failed`` / ``cancelled``

Run trigger types: ``manual``, ``scheduled``, ``retry``.

Run lifecycle
-------------
1. Trigger (manual / scheduled / retry) creates a run with injected clock.
2. Collectors execute (mock only); per-marketplace failures are isolated.
3. Valid listings become Price History snapshots.
4. Run is persisted with counts, duration_ms, error summaries, and retry
   visibility metadata.
5. Completed runs are **immutable** — further ``save_run`` mutations raise.

Idempotency behavior
--------------------
Manual ``POST /jobs/{job_id}/run`` accepts ``idempotency_key``.

- First request executes the job and stores ``key → run_id``.
- Duplicate requests with the same key return the original run.
- Empty keys are ignored.

Concurrent-run protection
-------------------------
A job cannot execute twice concurrently. Manual runs and scheduler due-runs
share a running lock (in-memory set + job.running flag). Concurrent attempts
raise ``409 Conflict``.

Retry behavior
--------------
Retry decisions reuse Sprint 8 ``CollectionRetryPolicy``:

- exponential delay recommendation (no sleeping)
- exposed fields: attempt, max_attempts, delay_seconds, next_retry_at,
  final_failure_reason
- domain and tests never sleep waiting for retries

Health versus readiness
-----------------------
``GET /health`` — liveness. Is the collection-operations subsystem loaded
and callable?

``GET /readiness`` — local dependency probes only (no network):

- job repository available
- run repository available
- price-history store available
- mock collectors registered and healthy
- scheduler callable
- no invalid job configuration

API endpoints
-------------
Base path: ``/api/v1/collection-operations``

- ``GET /status``
- ``GET /jobs`` (filters: status, marketplace, enabled)
- ``POST /jobs``
- ``GET /jobs/{job_id}``
- ``PATCH /jobs/{job_id}``
- ``DELETE /jobs/{job_id}``
- ``POST /jobs/{job_id}/pause``
- ``POST /jobs/{job_id}/resume``
- ``POST /jobs/{job_id}/run``
- ``GET /jobs/{job_id}/runs``
- ``GET /runs`` (``failed_only`` supported)
- ``GET /runs/{run_id}``
- ``POST /run-due``
- ``GET /health``
- ``GET /readiness``

Future background worker
------------------------
A future worker (cron, Celery beat, k8s CronJob, etc.) should:

1. Call ``CollectionOperationsService.run_due_jobs()`` (or
   ``POST /collection-operations/run-due``) on an interval.
2. Rely on built-in concurrent-run protection — overlapping ticks are safe.
3. Not implement its own sleep-based retries; use exposed retry metadata
   for observability only, or enqueue an explicit retry trigger later.
4. Keep mock/live collector selection outside this control plane.

Known limitations
-----------------
- In-memory job/run persistence only (process-local)
- No background threads, Celery, Redis, or APScheduler
- Mock collectors only — no live Shopee/Lazada/Amazon HTTP
- Idempotency keys are process-local
- Demo rate limits remain generous for interactive use
"""
