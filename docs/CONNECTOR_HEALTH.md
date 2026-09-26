"""Marketplace Connector Health — Sprint 18.

Status: implemented (in-memory tracker)
Date: 2026-07-29

Scope
-----
Track and expose connector operational health for demos, sync outcomes, and
API inspection. Health is advisory — it does not start background probes.

Statuses
--------
| Status | When |
|--------|------|
| ``healthy`` | Enabled, configured, recent success, no failure streak |
| ``degraded`` | Rate-limited or consecutive_failures > 0 (but < 3) |
| ``unavailable`` | consecutive_failures ≥ 3 or hard sync failure |
| ``disabled`` | Connector disabled in configuration |
| ``unconfigured`` | Missing config or never successfully synced |

Snapshot fields
---------------
``ConnectorHealth`` includes last attempted/successful sync, records
processed/failed, latency, rate-limit state, recent errors (no secrets),
checkpoint cursor, consecutive failures, and message.

Architecture
------------
```
build_health / derive_health_status
  ↔ InMemoryMarketplaceDataRepository.save_health / get_health
  ↔ MarketplaceSyncEngine updates after sync attempts
  ↔ GET /api/v1/marketplaces/connectors/{id}/health
```

Mock-live labeling
------------------
``MockLiveMarketplaceConnector.report_health()`` always carries the
**SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION** message. Degraded
status is used when simulated rate limiting is active.

Future stubs
------------
Official marketplace stubs report ``UNCONFIGURED`` and never claim healthy
live connectivity.

Limitations
-----------
- No Prometheus/Datadog exporters in this sprint
- No external uptime pingers
- In-memory only; process restart clears history
- No paging / notifications (later sprints)

Extension guide for official connectors
---------------------------------------
1. Implement ``report_health`` and ``report_rate_limit`` honestly.
2. Persist health via the repository after sync attempts.
3. Redact secrets from error details.
4. Add tests for healthy / degraded / unavailable / unconfigured paths.
5. Never mark a stub or scraper as healthy live.

Shopify Global Catalog PH provider status (Sprint 32 closure, 2026-09-25)
------------------------------------------------------------------------
This is the current connector-health record for the only production research
provider. It is not a second monitoring system and it does not probe Shopify.

| Field | Current value |
|-------|----------------|
| provider_id | ``ph-shopify-global-catalog`` |
| market | PH |
| certified capabilities | 4 (PRODUCT_DISCOVERY, OFFER_DISCOVERY, CURRENT_PRICING, AVAILABILITY) |
| operational_status | DISABLED |
| routing | none |
| live execution | unavailable |
| production profile | undeployed |

Monitoring must not call this provider healthy, live, available, or
production-ready while it is disabled. Registration and trusted
reduced-capability certification do not make the connector healthy.

Sprint 38 transition, not implemented here: when execution becomes
operational, connector health, execution traces, partial failure, 429,
timeout, quota, breaker, and kill-switch runtime monitoring become Sprint 38
responsibilities. Production alerts also remain Sprint 38 / 42. The deployed
operational kill-switch drill remains Sprint 38 / 41. Sprint 38 is unstarted.
"""
