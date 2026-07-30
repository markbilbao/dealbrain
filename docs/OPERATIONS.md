# Operations (Sprint 22)

**Status:** Sprint 22

## Day-2 runbook (demo / staging)

### Start

```bash
docker compose up --build -d
curl -s http://localhost:8000/live
curl -s http://localhost:8000/ready
```

### Inspect launch posture

```bash
curl -s http://localhost:8000/api/v1/launch/system-status
curl -s http://localhost:8000/api/v1/launch/feature-flags
curl -s -H "Authorization: Bearer demo-token-internal-admin" \
  http://localhost:8000/api/v1/launch/dashboard
```

### Demo personas

```bash
curl -s http://localhost:8000/api/v1/launch/demo
curl -s -X POST http://localhost:8000/api/v1/launch/demo/switch \
  -H "Content-Type: application/json" \
  -d '{"persona":"merchant"}'
```

### Configuration export (redacted)

```bash
curl -s -X POST -H "Authorization: Bearer demo-token-internal-admin" \
  http://localhost:8000/api/v1/launch/config/export
```

### Clear performance cache

```bash
curl -s -X POST -H "Authorization: Bearer demo-token-internal-admin" \
  http://localhost:8000/api/v1/launch/performance/clear
```

## Incident cues

| Symptom | Check |
|---------|-------|
| 503 on `/ready` | Database probe failed **or** production persistence NOT_READY |
| `/ready` `persistence_level=NOT_READY` | Missing migrations, memory backends in production, or DB down |
| 429 responses | Rate limit bucket exhausted |
| Missing security headers | `SECURITY_HEADERS_ENABLED` |
| Empty launch dashboard metrics | Stores not seeded / counters zero |
| Docs 404 in production | Expected unless `OPENAPI_PUBLIC_DOCS=true` |
| Sessions lost after restart | `USER_PLATFORM_BACKEND` still `memory` |

## Sprint 23 persistence ops

```bash
alembic upgrade head
# Verify readiness includes persistence components
curl -s http://localhost:8000/ready | jq '.persistence_level,.components'
```

Backup expectation: standard PostgreSQL backups cover `operational_entities` and prior tables. Launch config export remains settings-only (not a DB dump).

## What operators should not do

- Commit real API keys
- Enable live AI HTTP without vaulted keys
- Run production with `PERSISTENCE_BACKEND=memory`
- Expect simulated marketplace connectors or notification transports to be real
- Change DealScore weights via merchant/affiliate tools (impossible by design)
