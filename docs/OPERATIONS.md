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
| 503 on `/ready` | Database probe failed |
| 429 responses | Rate limit bucket exhausted |
| Missing security headers | `SECURITY_HEADERS_ENABLED` |
| Empty launch dashboard metrics | Memory stores not seeded / counters zero |
| Docs 404 in production | Expected unless `OPENAPI_PUBLIC_DOCS=true` |

## What operators should not do

- Commit real API keys
- Enable live AI HTTP without vaulted keys
- Expect this stack to be a production multi-region deployment
- Change DealScore weights via merchant/affiliate tools (impossible by design)
