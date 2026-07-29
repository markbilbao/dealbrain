# Production Configuration (Sprint 22)

**Status:** Sprint 22  
**Module:** `app/core/config.py`, `app/core/validation.py`

## Environments

| `APP_ENV` | Intent |
|-----------|--------|
| `development` | Local demo, docs on, seed mocks OK |
| `staging` | Beta rehearsal, stricter warnings |
| `production` | Strict validation, HSTS, no debug |

## Feature flags

| Flag | Default | Notes |
|------|---------|-------|
| `LAUNCH_READINESS_ENABLED` | true | Launch APIs + dashboard |
| `RATE_LIMITING_ENABLED` | true | HTTP rate limits |
| `SECURITY_HEADERS_ENABLED` | true | CSP/HSTS/frame options |
| `STRUCTURED_LOGGING_ENABLED` | true | JSON logs |
| `DEMO_LAUNCHER_ENABLED` | true | Persona switching |
| `PERFORMANCE_CACHE_ENABLED` | true | Short TTL read cache |
| `OPENAPI_PUBLIC_DOCS` | false | Force docs outside dev/staging |
| `LAUNCH_STRICT_STARTUP` | false | Fail boot on config errors |

Product flags from prior sprints (`USER_PLATFORM_ENABLED`, `AFFILIATE_ENABLED`,
`MERCHANT_PLATFORM_ENABLED`, …) remain independently toggleable.

## Startup validation

`run_startup_validation()` checks:

- Production: `APP_DEBUG` must be false; CORS must not be `*`
- Port / database URL sanity
- Rate limit floors
- Warnings for live AI HTTP without keys

Set `LAUNCH_STRICT_STARTUP=true` to abort boot on errors.

## Secure secret loading

- Secrets load from environment / `.env` via pydantic-settings
- Configuration export **always redacts** database URLs and API keys
- Config import never mutates runtime Settings and strips secret keys
- Never commit real production secrets — examples use empty placeholders

## Memory vs SQL backends

For beta rehearsal without a production DB, keep:

```
CANONICAL_REGISTRY_BACKEND=memory
PRICE_HISTORY_BACKEND=memory
```

Postgres remains available via docker-compose for optional SQL backends.
