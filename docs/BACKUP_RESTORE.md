# Backup & Restore (Sprint 22)

**Status:** Sprint 22  
**API:** `/api/v1/launch/config/export`, `/api/v1/launch/config/import`

## Scope

This sprint provides **configuration** backup/restore rehearsal — not a full
production database disaster-recovery system.

| Included | Not included |
|----------|--------------|
| Redacted settings export | Production DB dumps |
| Checklist state (in-memory) | Real secret vault backups |
| Import for review only | Automated offsite replication |

## Backup guide

### 1. Configuration export

```bash
curl -s -X POST \
  -H "Authorization: Bearer demo-token-internal-admin" \
  http://localhost:8000/api/v1/launch/config/export \
  | tee config-backup.json
```

Secrets (`DATABASE_URL`, AI keys) are always `***REDACTED***`.

### 2. List snapshots

```bash
curl -s -H "Authorization: Bearer demo-token-internal-admin" \
  http://localhost:8000/api/v1/launch/config/exports
```

### 3. Optional Postgres volume (compose)

```bash
docker compose exec db pg_dump -U dealbrain dealbrain > dealbrain-demo.sql
```

Only useful when SQL backends are enabled. Memory backends lose state on restart
by design.

## Restore guide

### Configuration import (review only)

```bash
curl -s -X POST \
  -H "Authorization: Bearer demo-token-internal-admin" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"app_env": "staging", "rate_limiting_enabled": true}}' \
  http://localhost:8000/api/v1/launch/config/import
```

Import **does not mutate runtime Settings**. Apply values via env files and
restart:

1. Copy desired keys into `.env` / orchestrator secrets
2. Restart API
3. Confirm `/api/v1/launch/system-status`

### Postgres restore (optional demo)

```bash
cat dealbrain-demo.sql | docker compose exec -T db psql -U dealbrain dealbrain
```

## Hard limitations

- No production secrets are backed up (they are never exported)
- In-memory merchant/user/affiliate stores are process-scoped
- This is a launch rehearsal aid, not enterprise DR
