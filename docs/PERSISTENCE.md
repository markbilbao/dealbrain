# Persistence (Sprint 23)

DealBrain uses SQLAlchemy + Alembic + PostgreSQL for durable state.

## Layers

1. **Sprint 7 (and product registry)** — async SQLAlchemy adapters (`postgresql+asyncpg`) for products, canonical registry, price snapshots.
2. **Sprint 23 operational stores** — sync SQLAlchemy adapters (`postgresql+psycopg`) implementing Sprint 17–21 repository ports via the shared `operational_entities` table.

## Adapter selection

| Environment | Default for Sprint 17–21 |
|-------------|--------------------------|
| development | `memory` (unless `PERSISTENCE_BACKEND=sqlalchemy`) |
| staging | follow explicit env; prefer sqlalchemy |
| production | `sqlalchemy` required; memory rejected |

See `app/infrastructure/persistence/binding.py` for the binding matrix.

## Local development

```bash
uv sync --extra dev
cp .env.example .env
docker compose up -d db
alembic upgrade head
# optional durable local mode:
# PERSISTENCE_BACKEND=sqlalchemy
uvicorn app.main:app --reload
```

## What persists

Users, sessions, profiles/preferences/settings, saved items, password-reset/verification/email-change records, marketplace offers/checkpoints/sync jobs, alert rules/events, notifications, affiliate merchants/links/clicks/attributions, merchant orgs/accounts/submissions/campaigns.

## What does not (yet)

Knowledge graph, personal AI profiles, shopping conversations, reviews, collection jobs, launch checklist — remain process-local by design until a later sprint owns durability for those domains.

## Transaction helper

`app/infrastructure/persistence/session.py` provides `sync_session` and `transaction`. Adapters commit per repository call by default; uniqueness conflicts map to `PersistenceConflictError` and domain validation errors.

### `seq` allocation

`OperationalStore._next_seq` computes `max(seq)+1` per store. It is **not** race-free under concurrent inserts: duplicate `seq` values are possible, and ordering tie-breaks on autoincrement `id`. This is documented and deferred rather than redesigned in Sprint 23 acceptance.
