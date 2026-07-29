# Monitoring (Sprint 22)

**Status:** Sprint 22

## Probes

| Endpoint | Meaning | Failure |
|----------|---------|---------|
| `GET /live` | Process alive | Restart container |
| `GET /ready` | Safe to receive traffic | Keep out of LB |
| `GET /health` | Detailed dependency report | Investigate deps |
| `GET /api/v1/live` | Versioned liveness | Same as `/live` |
| `GET /api/v1/ready` | Versioned readiness | Same as `/ready` |
| `GET /api/v1/health` | Versioned health | Same as `/health` |

Health payload includes:

- application status
- database status
- cache status
- version
- uptime
- dependency checks / feature toggles

## Structured logging

When `STRUCTURED_LOGGING_ENABLED=true`, logs are JSON lines with:

- `http_request` — method, path, status, duration_ms, request_id
- `auth_event` — authentication surface activity
- `affiliate_event` — affiliate route activity
- `merchant_event` — merchant/admin route activity

Sensitive values are redacted. Response headers include `X-Request-ID` and
`X-Response-Time-Ms`.

## Launch dashboard

`GET /api/v1/launch/dashboard` (admin) surfaces:

- users, watchlists, merchants, affiliate clicks
- alerts, notifications, products, offers, campaigns
- API health + system status
- feature flags + checklist progress
- cache hit/miss stats

## Performance cache

`GET /api/v1/launch/performance` reports TTL cache stats used to reduce
duplicate read processing for search/recommendations/dashboard aggregates.
Ranking order is never altered by the cache.
