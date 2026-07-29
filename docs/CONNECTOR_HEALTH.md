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
"""
