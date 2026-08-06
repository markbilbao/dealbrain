# Sprint 23 — Production Persistence and Operational Hardening

**Branch:** `sprint-23-production-persistence`
**Owner:** Persistence adapters / migrations / readiness depth (not domain logic)
**Architecture lock:** [docs/architecture/ARCHITECTURE_LOCK.md](architecture/ARCHITECTURE_LOCK.md)

## Investigation findings (Phase 1)

| Subsystem | Domain owner | Current repository | Default adapter (pre-23) | Persistence requirement | Migration risk | Sprint 23 adapter |
|-----------|--------------|--------------------|---------------------------|-------------------------|----------------|-------------------|
| Users / sessions / profiles | Sprint 17 | `UserRepository` et al. (`app/domain/interfaces/user_platform_repository.py`) | `InMemoryUserPlatformStore` (`app/user/memory.py`) | Required | Medium (email uniqueness) | `SqlAlchemyUserPlatformStore` |
| Marketplace sync / checkpoints | Sprint 18 | `MarketplaceDataRepository` | `InMemoryMarketplaceDataRepository` | Required | Medium (idempotency keys) | `SqlAlchemyMarketplaceDataRepository` |
| Alert rules / events | Sprint 19 | `AlertRuleRepository` / `AlertEventRepository` | `InMemoryAlertRuleRepository` | Required | Low (dedupe_key) | `SqlAlchemyAlertRuleRepository` |
| Notification center | Sprint 19 | `NotificationCenterRepository` | `InMemoryNotificationCenterRepository` | Required | Low | `SqlAlchemyNotificationCenterRepository` |
| Affiliate attribution | Sprint 20 | Affiliate ports in `affiliate_repository.py` | `InMemoryAffiliateRepository` | Required | Low | `SqlAlchemyAffiliateRepository` |
| Merchant platform | Sprint 21 | Merchant ports in `merchant_repository.py` | `InMemoryMerchantRepository` | Required | Medium (token/email indexes) | `SqlAlchemyMerchantRepository` |
| Canonical registry | Sprints 1–3 | `CanonicalProductStore` | memory (opt-in sqlalchemy) | Recommended | Existing | unchanged owner |
| Price history | Sprint 7 | `PriceHistoryStore` | memory (opt-in sqlalchemy) | Recommended | Existing | unchanged owner |
| Launch readiness | Sprint 22 | `LaunchHealthService` | shallow DB `SELECT 1` | Deep persistence checks added | Low | readiness consumer only |

**Runtime:** Python ≥3.12, FastAPI, SQLAlchemy 2 async (+ Sprint 23 sync `psycopg`), Alembic, pytest, FastAPI `Depends` DI, `pydantic-settings`.

## What became persistent

Operational aggregates for Sprints 17–21 are stored in `operational_entities` (JSON payload + secondary uniqueness keys) via SQLAlchemy sync adapters.

## What remains intentionally in-memory

- Reviews, review summaries, shopping conversations, knowledge graph, personal AI profiles (pre-17 / adjacent; not Sprint 23 ownership)
- Collection jobs/scheduler/rate limiter (Sprint 8/9)
- Launch checklist store / in-process rate limiter / TTL cache (Sprint 22 infrastructure)
- Marketplace connectors remain fixture/simulated (no real HTTP)

## Production adapter selection

| Interface group | Persistent impl | Test/demo impl | Selection |
|-----------------|-----------------|----------------|-----------|
| User platform ports | `SqlAlchemyUserPlatformStore` | `InMemoryUserPlatformStore` | `USER_PLATFORM_BACKEND` / `PERSISTENCE_BACKEND`; production defaults to sqlalchemy |
| Marketplace data | `SqlAlchemyMarketplaceDataRepository` | `InMemoryMarketplaceDataRepository` | `MARKETPLACE_DATA_BACKEND` |
| Alerts | `SqlAlchemyAlertRuleRepository` | `InMemoryAlertRuleRepository` | `ALERTS_BACKEND` |
| Notifications | `SqlAlchemyNotificationCenterRepository` | `InMemoryNotificationCenterRepository` | `NOTIFICATIONS_BACKEND` |
| Affiliate | `SqlAlchemyAffiliateRepository` | `InMemoryAffiliateRepository` | `AFFILIATE_BACKEND` |
| Merchant | `SqlAlchemyMerchantRepository` | `InMemoryMerchantRepository` | `MERCHANT_BACKEND` |

Production **cannot** silently fall back to memory. Startup validation and `assert_production_persistence` fail closed.

## Security hardening

- `ALLOW_DEMO_RESET_TOKENS` / password-reset and email-verification raw tokens omitted in production
- `DEMO_LAUNCHER_ENABLED` must be false in production
- `SEED_DEMO_DATA` must be false in production; SQLAlchemy affiliate/merchant constructors default to `seed=False` (opt-in)
- Demo seeding for durable SQL stores is explicit via `SEED_DEMO_DATA=true` in non-production only

## Tests (Sprint 23 acceptance)

Covered under `tests/unit/persistence/`:

- User/alert contract + restart (original suite)
- Marketplace / notifications / affiliate / merchant restart + upsert
- Concurrent duplicate registration, alert dedupe, attribution upsert
- Transaction rollback
- User-scoped alert/notification listing and merchant membership isolation
- Architecture neutrality

## Known deferred concurrency note

`OperationalStore._next_seq` is a best-effort insertion-order hint. Concurrent writers may allocate duplicate `seq` values; `list()` orders by `(seq, id)`. Entity uniqueness remains on `(store, entity_id)` / `(store, secondary_key)`. A dedicated sequence allocator is deferred (would be a broader redesign).

## Deferred (historical bucket — superseded for ownership)

> **Superseded for sprint ownership:** The former undifferentiated “Sprints 24–40” deferred bucket is replaced by explicit Global Public Beta sprint ownership in [`docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) (endpoint Sprint 46). Sprint identities 24–40 remain historical.

| Deferred item (Sprint 23 era) | Current owning sprint(s) |
|-------------------------------|--------------------------|
| Real marketplace connectors | 31–36, 38 |
| Real email / SMS / push | 27 (email); SMS/push post-beta unless re-scoped |
| Large UI / consumer web | 29 |
| Redis rate limiting/cache, WAF/CDN depth | 40 / 41 decision; depth often post-beta |
| Billing | Post-beta (`n_a_beta`) |
| Full merchant ingestion into organic offers | 31 + market sprints |
| Distributed workers | 43 review / post-beta |
| AI provider expansion / mobile apps / ranking changes | Post-beta unless master roadmap amended |

Original deferred list (preserved): real marketplace connectors, distributed workers, real email/SMS/push, Redis rate limiting/cache, WAF/CDN, billing, full merchant ingestion into organic offers, AI provider expansion, mobile apps, ranking/recommendation changes, large UI redesign.

## Definition of Done posture

See final report in the Sprint 23 completion notes. Disposition target: **COMPLETE WITH DOCUMENTED LIMITATIONS** (watchlists/collection/KG still memory; connectors still simulated).
