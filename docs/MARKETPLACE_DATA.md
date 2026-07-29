"""Marketplace Data Synchronization — Sprint 18.

Status: implemented (fixture / imported / simulated-live only)
Date: 2026-07-29

Scope
-----
Provider-neutral infrastructure to ingest, normalize, synchronize, and query
marketplace product / offer / price / inventory data with explicit source modes.
This sprint does **not** scrape live Shopee, Lazada, Amazon, TikTok Shop, or
eBay; does not store real marketplace credentials; and does not run an external
scheduler.

Source modes
------------
- ``fixture`` — deterministic demo/canned data (never current live pricing)
- ``imported`` — structured CSV/JSON file imports (never live)
- ``live`` — returned by a configured live connector; Sprint 18 only ships
  ``MockLiveMarketplaceConnector``, which is **SIMULATED LIVE — NOT A REAL
  MARKETPLACE CONNECTION**

Architecture
------------
```
API (/api/v1/marketplaces/..., /api/v1/products/{id}/price-history|inventory-history)
  → MarketplaceDataService
      → MarketplaceConnectorRegistry
          → FixtureMarketplaceConnector
          → ImportedMarketplaceConnector
          → MockLiveMarketplaceConnector (simulated)
          → Future official stubs (Shopee/Lazada/Amazon/TikTok Shop/eBay — not implemented)
      → ImportPipeline (CSV/JSON validation, mapping, duplicates, partial imports)
      → MarketplaceRecordNormalizer + DataFreshness rules
      → MarketplaceProductMatcher
      → MarketplaceSyncEngine (full/incremental, checkpoints, advisory retries)
      → InMemoryMarketplaceDataRepository
```

Domain highlights
-----------------
- ``MarketplaceSource`` / ``MarketplaceConnectorInfo`` — mode, capabilities, labels
- ``MarketplaceOffer`` — normalized offer with provenance + freshness
- ``RawMarketplaceRecord`` — preserved raw payload + content hash
- ``ImportBatch`` / ``ImportRecord`` — import lifecycle and per-row outcomes
- ``SyncJob`` / ``SyncCheckpoint`` / ``SyncConflict`` — sync orchestration
- ``ConnectorHealth`` — healthy / degraded / unavailable / disabled / unconfigured
- ``DataFreshness`` — fresh / aging / stale / unknown (fixture never ``is_current_live_price``)

API surface (selected)
----------------------
| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/marketplaces/sources` | No |
| GET | `/api/v1/marketplaces/connectors` | No |
| GET | `/api/v1/marketplaces/connectors/{id}` | No (secrets redacted) |
| POST | `/api/v1/marketplaces/connectors/{id}/test` | Yes (ops) |
| GET | `/api/v1/marketplaces/connectors/{id}/health` | No |
| POST | `/api/v1/marketplaces/imports` | Yes (ops) |
| GET | `/api/v1/marketplaces/imports/{batch_id}` | No |
| POST | `/api/v1/marketplaces/sync` | Yes (ops) |
| GET | `/api/v1/marketplaces/offers` | No |
| POST | `/api/v1/marketplaces/demo/seed` | Yes (ops) |
| GET | `/api/v1/products/{id}/price-history` | No |
| GET | `/api/v1/products/{id}/inventory-history` | No |

Integrations
------------
Shopping Assistant and DealScore optionally consume ``MarketplaceDataService``
for provenance / freshness notes. Anonymous shopping still works when the
collaborator is absent or empty.

Limitations
-----------
- No scraping; no real marketplace HTTP clients
- No real credentials; secrets are redacted in APIs and audit logs
- In-memory persistence only (process-scoped)
- No external scheduler (Celery, cron, APScheduler, Redis)
- No notifications, affiliate, ads, merchant dashboards, or subscriptions
  (later sprints)
- Future official connectors are stubs only

See also
--------
``CONNECTOR_ARCHITECTURE.md``, ``DATA_IMPORTS.md``, ``DATA_NORMALIZATION.md``,
``SYNC_ENGINE.md``, ``DATA_FRESHNESS.md``, ``CONNECTOR_HEALTH.md``
"""
