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

Sprint 38 engineering foundation (2026-09-26) is **IN PROGRESS** and is not
complete. Connector health for this disabled provider stays not healthy, not
live, and not available. The foundation adds a separate health report and
refuses Shopify execution without a network call. Production alerts and
paging remain Sprint 42. The deployed operational kill-switch drill remains
Sprint 38 / 41. Sprint 38 overall status is IN PROGRESS. Live research
operational status is a separate fact, ``NOT OPERATIONAL``. Routing remains
absent and production readiness remains false. Authorization and planning
handoff can prepare a request and still must not describe this disabled
provider as attempted, checked, or live.

Sprint 38 reliability state (2026-09-27) persists research-provider circuit
breakers in the existing ``operational_entities`` store, namespace
``research.provider_reliability``. That is separate from Sprint 18
``marketplace_data.health``. No new table and no migration were added. The
scripted connector breaker remains in-memory chaos-test state and is not this
record. An absent row is closed and is not itself a seeded production failure.

The current Shopify provider remains certified for the reduced capability set,
operationally disabled, not healthy, merchant availability false, and live
false. A closed breaker, certification, routing absence, and ``/ready`` do not
change that. ``/ready`` stays independent of merchant availability. Kill switch
and ``DISABLED`` are stronger than the breaker. Breaker-worthy categories are
timeout, unavailable, and unknown. Rate limit, quota, credential, kill switch,
circuit-open, and partial results are recorded and do not open the breaker.
The certified Shopify path still does not retry. This slice does not probe,
page, or call Shopify. Alerts, paging, synthetic probes, and incident
operations remain Sprint 42. Durable authorized-execution records remain a
later Sprint 38 slice. Sprint 38 stays IN PROGRESS. Live execution stays
NOT OPERATIONAL.
