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

`run_startup_validation()` is the authoritative fail-closed path:

- Production: `APP_DEBUG` must be false; CORS must not be `*`
- Production: demo seed/launcher/reset tokens off; `PRICE_HISTORY_SEED_DEMO_MOCK` off
- Production: `LAUNCH_STRICT_STARTUP` must be true; structured logging on; log level not DEBUG
- Production: `DATABASE_URL` must be PostgreSQL with a non-placeholder password
- Production: `APP_SECRET_KEY` present and strong (min 32 chars; value never logged)
- Port / database URL sanity
- Rate limit floors
- Warnings for live AI HTTP without keys (fatal in production when live HTTP is on)

**Contract:** when `APP_ENV=production`, invalid mandatory configuration raises
regardless of `LAUNCH_STRICT_STARTUP`. The flag strengthens non-production boots but
must not weaken production. Application lifespan calls this helper only — it does not
re-implement a second raise path. Error text names field categories and never includes
secret values.

## Secure secret loading

- Secrets load from environment / `.env` via pydantic-settings
- Configuration export **always redacts** database URLs and API keys
- Config import never mutates runtime Settings and strips secret keys
- Never commit real production secrets — examples use empty placeholders
- Cloud RDS master passwords are AWS-managed (Secrets Manager); Terraform stores
  secret ARNs only (see [SPRINT_25A_INFRASTRUCTURE.md](SPRINT_25A_INFRASTRUCTURE.md))
- Production runtime images must be pulled by **immutable digest** from GHCR
  (`ghcr.io/<owner>/<repo>@sha256:…`), never by mutable tags such as `latest` or
  `ci-latest` (see [SPRINT_25B_IMAGE_PUBLICATION.md](SPRINT_25B_IMAGE_PUBLICATION.md)).
  Staging/production promotion workflows are not implemented in Sprint 25b.1.
- Sprint 25b.2 models OIDC deploy roles and GHCR pull secret **containers**
  (`dealbrain/<env>/ghcr_pull`) for a classic PAT with `read:packages` only.
  Secret **values** (including the PAT) are never stored in Terraform or git.
  Deploy roles cannot read Secrets Manager values; hosts retrieve them.
  Roles remain **non-operational** until GitHub Environment hard gates are live
  (`staging` / `production` exact names, `main`-only deployment branches,
  production required reviewers, admin bypass disabled or formally audited).
  See [SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md](SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md).

## Memory vs SQL backends

For beta rehearsal without a production DB, keep:

```
CANONICAL_REGISTRY_BACKEND=memory
PRICE_HISTORY_BACKEND=memory
```

Postgres remains available via docker-compose for optional SQL backends.
