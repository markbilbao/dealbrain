# Launch Readiness (Sprint 22)

**Status:** Sprint 22  
**Package:** `app/launch/`  
**Services:** `LaunchHealthService`, `LaunchDashboardService`, `LaunchDemoService`, `LaunchConfigService`, `LaunchPerformanceService`  
**API:** `/health`, `/ready`, `/live`, `/api/v1/health`, `/api/v1/ready`, `/api/v1/live`, `/api/v1/launch/*`

## Overview

Sprint 22 prepares DealBrain for a **public beta launch rehearsal** without
real cloud deployment, production databases, payments, or production secrets.

Everything remains **demo / in-memory safe**.

**Hard rules preserved:**
- Organic DealScore ranking is unchanged
- Affiliate generation remains post-rank only
- Merchant isolation is preserved
- Prior sprint APIs continue to work

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

- No real cloud deployment
- No production database
- No payment processing
- No real email / SMS / push
- No subscription billing
- No production secrets
