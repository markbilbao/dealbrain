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
record. An absent row is closed at revision 0. A stored row is the
authoritative breaker for production research-provider health. Callers inject
the repository. The health function does not open a database connection and
does not invent a closed breaker when a row exists.

``PRODUCTION_BREAKER_PERSISTED`` means the production repository survives
process and service recreation. It does not mean production has been deployed,
that a breaker row already exists, or that the breaker has been live-validated.

Operational availability is provider status, kill switch, and a closed breaker.
Merchant availability uses that serving contract. Healthy requires that
eligibility plus a recorded successful attempt. Static ``AVAILABLE`` status is
not a healthy claim. Live is actual live execution and stays false. The
current Shopify provider remains certified for the reduced capability set,
operationally disabled, not healthy, merchant availability false, and live
false. A closed breaker, certification, routing absence, and ``/ready`` do not
change that. ``/ready`` stays independent of merchant availability. Kill switch
and ``DISABLED`` are stronger than the breaker. Breaker-worthy categories are
timeout, unavailable, and unknown. Rate limit, quota, credential, kill switch,
circuit-open, and partial results are recorded and do not open the breaker.
The certified Shopify path still does not retry.

A future live connector attempt must consult provider status, the kill switch,
and the persisted breaker. A passed live-mode gate is not sufficient while the
persisted breaker is open. That permission path does not perform HTTP, because
live execution is not operational. This slice does not probe, page, or call
Shopify. Alerts, paging, synthetic probes, and incident operations remain
Sprint 42. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL.

Durable authorized-execution preparation (2026-09-27) stores one
``prepared_unavailable`` row in ``operational_entities`` /
``research.authorized_executions``. That row survives a new repository and a
new database session. It does not consume the authorization, check a source,
or perform HTTP. A database outage during preparation fails closed as
``blocked_persistence`` and leaves the confirmation response non-live.
Future live start is a claim transaction, then a connector attempt outside
that transaction, then a later outcome transaction. Connector HTTP is not
inside one database transaction. The HALF_OPEN single-probe lease remains
required before a connector attempt. Sprint 38 stays IN PROGRESS. Live
execution stays NOT OPERATIONAL.

Safe live-start claim (2026-09-30) reserves one future connector attempt as
``claimed_for_attempt`` and, when the persisted breaker is HALF_OPEN, one
provider/market probe lease. Both use the existing ``operational_entities``
rows and compare-and-swap. No new table. The raw claim capability is not
stored. A claim is not a source attempt and not provider health evidence.
The sentence in this paragraph that said a claim is not authorization
consumption is historical for that slice. The later authorization-consumption
slice consumes the exact authorization inside a successful claim transaction.
Current Shopify production state cannot acquire either reservation.
``SHOPPING_RESEARCH_EXECUTION_MODE`` stays disabled. Production deployment
remains Sprint 41. Alerts, paging, and synthetic probes remain Sprint 42.

Sprint 38 closure-readiness audit (2026-09-30, corrected before merge)
is the current reading. Engineering stays IN PROGRESS. The shopper path
stops at durable preparation and does not call the claim or the adapter.
Positive composition and canonical-results plumbing remain Sprint 38.
Sprint 38 stays IN PROGRESS and is not COMPLETE / CLOSED. Live execution
stays NOT OPERATIONAL. The Shopify adapter records an authoritative trace
and a durable outcome only for an injected fake transport. Production
composition never calls that transport and still returns
``production_execution_not_wired``. Real Shopify calls stay 0. The provider
stays DISABLED, not healthy, not live, and not available. Routing stays
absent. Public certified shopping markets stay 0. The production UCP profile
stays undeployed. Repository kill-switch checks are not a deployed drill;
that drill remains Sprint 41. Alerts, paging, and synthetic production
probes remain Sprint 42. The HALF_OPEN lease is not a production probe.
Query-time policy still refuses persistent Shopify cache admission. Audit:
``docs/roadmap/evidence/SPRINT_38_CLOSURE_READINESS_AUDIT_2026-09-30.md``.
