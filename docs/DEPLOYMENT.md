# Deployment (Sprint 22)

**Status:** Sprint 22  
**Related:** [PRODUCTION.md](PRODUCTION.md), [MONITORING.md](MONITORING.md)

## Local development

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- Demo UI: http://localhost:8000/demo
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Docker

```bash
docker compose up --build -d
docker compose --profile migrate up migrate
```

### Services

| Service | Role |
|---------|------|
| `api` | FastAPI + uvicorn |
| `db` | Postgres 16 (optional for memory backends) |
| `migrate` | Alembic upgrade (profile `migrate`) |

### Health checks

- Container HEALTHCHECK uses `GET /live` (liveness)
- Orchestrators should also probe `GET /ready` before routing traffic
- Detailed dependency report: `GET /health` or `GET /api/v1/health`

## Production-style startup (still demo-safe)

```bash
APP_ENV=production \
APP_DEBUG=false \
PRICE_HISTORY_SEED_DEMO_MOCK=false \
CANONICAL_REGISTRY_BACKEND=memory \
PRICE_HISTORY_BACKEND=memory \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> This sprint does **not** perform a real cloud deployment. Use compose locally
> or in a staging VM for rehearsal only.

## Environment examples

| File | Purpose |
|------|---------|
| `.env.example` | Local development defaults |
| `.env.staging.example` | Staging / beta rehearsal |
| `.env.production.example` | Production-shaped (no real secrets) |

## Rollback

1. Stop the API container / process
2. Restore prior image/tag or git revision
3. Re-apply previous env file
4. Confirm `/live` and `/ready`
5. See [BACKUP_RESTORE.md](BACKUP_RESTORE.md) for config snapshot restore
