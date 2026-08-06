# Launch Readiness (Sprint 22)

**Status:** Sprint 22

**Package:** `app/launch/`

**Services:** `LaunchHealthService`, `LaunchDashboardService`, `LaunchDemoService`, `LaunchConfigService`, `LaunchPerformanceService`

**API:** `/health`, `/ready`, `/live`, `/api/v1/health`, `/api/v1/ready`, `/api/v1/live`, `/api/v1/launch/*`

**Global Public Beta roadmap:** [`roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) (endpoint **Sprint 46**; Sprint 30 audit persisted as NOT READY)

## Overview

Sprint 22 prepares DealBrain for a **public beta launch rehearsal**.
Sprint 23 adds **durable operational persistence** and deeper readiness checks
for Sprints 17–21 while Sprint 22 remains the readiness owner.

> **Roadmap note (2026-08-06):** Sprint 22 readiness APIs alone do **not** constitute Global Public Beta.
> Global Public Beta exit criteria and sprint ownership live in the master roadmap.
> Prior “Sprint 30 public launch” / “Sprint 40 hard endpoint” sequencing statements are superseded there.

**Hard rules preserved:**
- Organic DealScore ranking is unchanged
- Affiliate generation remains post-rank only
- Merchant isolation is preserved
- Prior sprint APIs continue to work

## Readiness levels (Sprint 23)

`/ready` reports `persistence_level`:

| Level | Meaning |
|-------|---------|
| LIVE | Process up (`/live` only) |
| READY | DB up + required production persistence bindings/schema OK |
| DEGRADED | Non-fatal gaps (e.g. staging memory backends) |
| NOT_READY | Production memory adapters, missing schema, or DB down |

Checks distinguish **shallow** (`SELECT 1`) vs **deep** (`operational_entities` + adapter bindings).
Simulated connectors/transports are never labeled as live integrations.

See also [PERSISTENCE.md](PERSISTENCE.md) and [SPRINT_23_PRODUCTION_PERSISTENCE.md](SPRINT_23_PRODUCTION_PERSISTENCE.md).

## Architecture

```
Probes (/health /ready /live)
      │
      ▼
LaunchHealthService ──► DB probe + cache + flags
      │
Launch APIs (/api/v1/launch/*)
      ├─ dashboard (admin metrics)
      ├─ demo launcher (personas)
      ├─ feature flags
      ├─ checklist
      ├─ config export/import (redacted)
      └─ performance cache stats
      │
Middleware
      ├─ RequestLoggingMiddleware (structured, redacted)
      ├─ RateLimitMiddleware (configurable buckets)
      ├─ SecurityHeadersMiddleware (CSP/HSTS/…)
      └─ CORS (existing)
      │
Global error handlers → consistent JSON (+ legacy detail)
```

## Documentation map

| Doc | Purpose |
|-----|---------|
| [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) | Go-live checklist |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker / compose / startup |
| [PRODUCTION.md](PRODUCTION.md) | Production configuration |
| [SECURITY.md](SECURITY.md) | Launch security controls |
| [OPERATIONS.md](OPERATIONS.md) | Day-2 ops |
| [MONITORING.md](MONITORING.md) | Health / logs / metrics |
| [BACKUP_RESTORE.md](BACKUP_RESTORE.md) | Backup & restore guides |

## Limitations

- No real cloud deployment *(staging path exists under Sprint 25b.*; production cutover owned by Sprints 41–45)*
- No production database *(planned Sprint 41)*
- No payment processing
- No real email / SMS / push *(real transactional email owned by Sprint 27)*
- No subscription billing
- No production secrets *(Sprint 41)*

See also [`roadmap/GAP_INVENTORY.md`](roadmap/GAP_INVENTORY.md).
