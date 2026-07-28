"""Watchlists & Price Alerts — Sprint 10.

Status: implemented (in-memory + mock notifications only)
Date: 2026-07-28

Scope
-----
Track products on watchlists and evaluate price / DealScore alert conditions
on demand. Integrates with Product Identity, Price History, DealScore, and
Collection systems as **read-only** collaborators. This sprint does **not**
send real notifications, start background workers, call LLMs, or modify
protected intelligence modules.

Architecture
------------
```
API (/api/v1/watchlists, /api/v1/alerts)
  → WatchlistService / AlertService
      → WatchlistRepository / AlertRepository (in-memory)
      → PriceHistoryService (current price, historical low)
      → DealRecommendationService (optional DealScore reads)
      → CanonicalProductRegistry (optional identity soft-check)
      → MockNotificationService (queued receipts only)
```

Alert types
-----------
- ``price_drop`` — current total cost is lower than ``last_known_price``
- ``target_price_reached`` — current total cost ≤ item ``target_price``
- ``dealscore_improved`` — recommended DealScore rose vs ``last_known_dealscore``
- ``historical_low`` — current total cost equals / sets a new historical low
  (lowest recorded in available DealBrain history; requires ≥2 observations)

Evaluation is **manual only** via ``POST .../check-alerts``. After each
evaluation, item baselines (``last_known_price``, ``last_known_dealscore``,
``last_historical_low``) are updated so subsequent checks are differential.

Notifications
-------------
``MockNotificationService`` always returns ``status: queued`` on channel
``mock``. No email, SMS, push, or third-party provider is contacted.

API endpoints
-------------
Base paths: ``/api/v1/watchlists`` and ``/api/v1/alerts``

Watchlists:

- ``GET /watchlists``
- ``POST /watchlists``
- ``GET /watchlists/{watchlist_id}``
- ``PATCH /watchlists/{watchlist_id}``
- ``DELETE /watchlists/{watchlist_id}``
- ``GET /watchlists/{watchlist_id}/items``
- ``POST /watchlists/{watchlist_id}/items``
- ``GET /watchlists/{watchlist_id}/items/{item_id}``
- ``PATCH /watchlists/{watchlist_id}/items/{item_id}``
- ``DELETE /watchlists/{watchlist_id}/items/{item_id}``
- ``GET /watchlists/{watchlist_id}/alerts``
- ``POST /watchlists/check-alerts``
- ``POST /watchlists/{watchlist_id}/check-alerts``

Alerts:

- ``GET /alerts``
- ``GET /alerts/{alert_id}``
- ``POST /alerts/{alert_id}/acknowledge``
- ``POST /alerts/{alert_id}/dismiss``

Sample JSON payloads
--------------------

Create watchlist::

    POST /api/v1/watchlists
    {
      "name": "Phones to watch",
      "owner_id": "demo-user",
      "description": "iPhone deals",
      "enabled": true
    }

Response::

    {
      "watchlist_id": "a1b2c3d4-...",
      "name": "Phones to watch",
      "owner_id": "demo-user",
      "description": "iPhone deals",
      "enabled": true,
      "created_at": "2026-07-28T13:00:00+00:00",
      "updated_at": "2026-07-28T13:00:00+00:00",
      "item_count": 0
    }

Add item (use Price History demo canonical id)::

    POST /api/v1/watchlists/{watchlist_id}/items
    {
      "canonical_product_id": "00000000-0000-4000-8000-000000000017",
      "product_label": "iPhone 17 Pro Max 256GB",
      "target_price": 74000,
      "currency": "PHP",
      "search_query": "iPhone 17 Pro Max",
      "last_known_price": 76000,
      "last_known_dealscore": 72.0,
      "last_historical_low": 73990
    }

Check alerts::

    POST /api/v1/watchlists/{watchlist_id}/check-alerts

Response (truncated)::

    {
      "watchlist_ids": ["a1b2c3d4-..."],
      "items_checked": 1,
      "alerts_count": 2,
      "alerts_created": [
        {
          "alert_id": "...",
          "alert_type": "price_drop",
          "message": "Price dropped by PHP 1500.00 (76000.00 → 74500.00).",
          "status": "notified",
          "..."
        }
      ],
      "notifications": [
        {
          "notification_id": "...",
          "channel": "mock",
          "status": "queued",
          "detail": "Queued mock notification ... No email/SMS/push sent."
        }
      ],
      "evaluated_at": "2026-07-28T13:05:00+00:00",
      "disclaimer": "Notifications are mock-only ..."
    }

Protected modules (unchanged)
-----------------------------
- Product Parser
- Product Identity
- Product Matching
- DealScore Engine
- Recommendation Engine
- Price History statistics
- Marketplace Collection Infrastructure
- Collection Operations & Monitoring

Known limitations
-----------------
- In-memory persistence only (process-local; no DB migrations)
- No background workers, Celery, Redis, or APScheduler
- Mock notifications only
- DealScore enrichment requires a ``search_query`` (or product label) and
  uses existing marketplace mock connectors
- Alert evaluation is explicit / manual — nothing polls in the background
"""
