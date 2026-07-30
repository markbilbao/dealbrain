# Database Migrations

DealBrain uses **Alembic** with async online migrations (`alembic/env.py`) against `DATABASE_URL`.

## Commands

```bash
# Apply all migrations
alembic upgrade head

# Show current revision
alembic current

# Downgrade one revision (use with care)
alembic downgrade -1
```

## Sprint 23 migration

- Revision: `d4e5f6a7b8c9_sprint23_operational_entities`
- Parent: `c3d4e5f6a7b8` (price snapshots)
- Creates `operational_entities` for Sprint 17–21 durable aggregates

### Schema summary

| Table | Owning sprint | PK | Important keys | Uniqueness | Indexes | Retention |
|-------|---------------|----|----------------|------------|---------|-----------|
| `operational_entities` | 23 (adapters for 17–21) | `id` | `store`, `entity_id`, `secondary_key`, `owner_id`, `payload`, `seq` | `(store, entity_id)`, `(store, secondary_key)` | `(store, owner_id)`, `(store, seq)` | Operational; backup with Postgres |

Domain meaning is encoded in `store` namespaces (see `app/infrastructure/persistence/stores.py`), for example:

- `user_platform.users` — secondary_key = normalized email
- `user_platform.sessions` — secondary_key = token_hash
- `alerts.events` — secondary_key = dedupe_key
- `marketplace_data.offers` / content-hash index stores
- `affiliate.*`, `merchant.*`, `notifications.*`

### Existing durable tables (pre-23)

| Table | Owning sprint | Notes |
|-------|---------------|-------|
| `products` | 1–3 | unique `manufacturer_sku` |
| `canonical_products` / relations | 1–3 | unique `identity_key` |
| `price_snapshots` | 7 | unique observation key |

## Policy

- Seed/demo data is **not** part of schema migrations.
- No destructive drops without explicit warning and review.
- Downgrade support: Sprint 23 downgrade drops `operational_entities` only.
