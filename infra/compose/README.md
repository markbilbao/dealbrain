# Sprint 25a — GHCR-compatible Compose overlays

Root `docker-compose.yml` remains the **local/dev** baseline (includes Postgres).

Cloud staging/production use these overlays against **RDS** — no `db` service.

## Files

| File | Role |
|------|------|
| `docker-compose.base.yml` | Shared `api` + one-shot `migrate` |
| `docker-compose.staging.yml` | Staging env defaults |
| `docker-compose.production.yml` | Production fail-safe defaults |

## Requirements

- Same `DEALBRAIN_IMAGE` (immutable digest) for `api` and `migrate`
- `migrate` is profile `migrate` / one-shot (`restart: "no"`)
- `api` does **not** run Alembic
- Secrets via environment injection — never committed
- Container HEALTHCHECK → `GET /live`; ALB → `GET /ready`

## Example

```bash
export DEALBRAIN_IMAGE=ghcr.io/EXAMPLE_ORG/dealbrain@sha256:abc…
export DATABASE_URL='postgresql+asyncpg://…'   # assembled at deploy (25b) from AWS-managed RDS secret + endpoint
export CORS_ORIGINS='https://api.dealbrain.example'
export APP_SECRET_KEY='…'

docker compose \
  -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml \
  --profile migrate run --rm migrate

docker compose \
  -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml \
  up -d
```

## Validate config (no deploy)

```bash
DEALBRAIN_IMAGE=ghcr.io/EXAMPLE_ORG/dealbrain:test \
DATABASE_URL=postgresql+asyncpg://u:p@host:5432/dealbrain \
CORS_ORIGINS=https://example.com \
APP_ENV=production \
docker compose \
  -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml \
  config
```
