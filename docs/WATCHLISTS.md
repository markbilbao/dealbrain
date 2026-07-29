# Watchlists (Sprint 19 — Authenticated Platform)

**Status:** Sprint 19
**Predecessor:** [`WATCHLISTS_V1.md`](WATCHLISTS_V1.md) (Sprint 10 — anonymous, in-memory watchlists & mock alerts)
**Extension service:** `ExtendedWatchlistService` in `app/services/watchlist_service_ext.py`
**Store:** `InMemoryWatchlistStore` in `app/watchlists/memory.py`
**Security helpers:** `app/watchlists/security.py`
**Domain entities:** `app/domain/entities/watchlist.py`
**Repository ports:** `app/domain/interfaces/watchlist_repository.py`

## Overview

Sprint 19 layers ownership, lifecycle, and richer item metadata on top of the
Sprint 10 watchlist primitives described in `WATCHLISTS_V1.md`. It does this
strictly by **extension**: `app.services.watchlist_service.WatchlistService`
and `app.intelligence.watchlists.memory.InMemoryWatchlistRepository` are
protected Sprint 10 modules and are never edited in place.
`ExtendedWatchlistService` subclasses the Sprint 10 service and
`InMemoryWatchlistStore` subclasses the Sprint 10 repository, so every prior
method signature and behavior keeps working unchanged for existing callers
and tests.

New in Sprint 19:

- **Bearer-token authentication and per-owner access control** — watchlists
  are scoped to the authenticated user (`owner_id`) via `UserPlatformService`.
- **Multiple watchlists per user**, including a single **default** watchlist
  (`is_default`) used by Shopping Assistant "add to watchlist" flows.
- **Lifecycle**: `active` → `paused` → `resumed` / `archived`
  (`WatchlistStatus`).
- **Marketplace-offer items** (`item_kind=offer`), not just canonical
  products.
- **Preferred sellers / marketplaces** at both the watchlist and item level.
- **Idempotent item adds** (`add_item_idempotent`) — re-adding the same
  product returns the existing item instead of raising.
- **Item notes** and **per-item monitoring pause**.
- **Watchlist history** — an append-only audit trail of lifecycle and
  membership changes, used to power dashboard "recent activity".

## Architecture

```
API (/api/v1/watchlists, /api/v1/alerts)
  Authorization: Bearer <access_token>  (optional if WATCHLISTS_REQUIRE_AUTH=false)
      │
      ▼
  _resolve_actor()  ──►  UserPlatformService.require_user(token)  ──► user_id
      │
      ▼
  ExtendedWatchlistService  (extends WatchlistService — Sprint 10, protected)
      ├─ require_owner()              — 403 on cross-owner access
      ├─ create/list/update/delete_watchlist(owner_id=...)
      ├─ pause / resume / archive_watchlist()
      ├─ set_watchlist_preferred_sellers / _marketplaces()
      ├─ add_item_idempotent() / add_offer()
      ├─ set_item_notes / pause_item_monitoring / set_item_preferred_*()
      ├─ get_history()
      │
      ├─► InMemoryWatchlistStore (extends InMemoryWatchlistRepository — Sprint 10, protected)
      ├─► PriceHistoryService        (current price, historical low — read-only)
      ├─► DealRecommendationService  (optional DealScore reads — read-only)
      ├─► CanonicalProductRegistry   (optional identity soft-check — read-only)
      └─► WatchlistAuditLogger       (in-process audit buffer, best-effort)
```

## Authentication & ownership

- Controlled by `settings.watchlists_require_auth` (`WATCHLISTS_REQUIRE_AUTH`,
  default `true`).
- When enabled, every watchlist/item/history/preferred-seller endpoint
  requires `Authorization: Bearer <access_token>` (obtained from
  `POST /api/v1/auth/login` or `/api/v1/auth/register` — see
  [`USER_PLATFORM.md`](USER_PLATFORM.md)). A missing or invalid token returns
  `401`.
- A watchlist with `owner_id is None` (e.g. a Sprint 10 fixture) is treated
  as unowned/shared and is accessible to any caller — this keeps every
  Sprint 10 test and demo fixture working unmodified.
- Accessing a watchlist owned by a *different* authenticated user returns
  `403 Forbidden` (`WatchlistOwnershipError`).
- When `WATCHLISTS_REQUIRE_AUTH=false` (demo/backward-compat mode), requests
  may fall back to a body-supplied `owner_id` with no token, matching the
  original Sprint 10 behavior exactly.

## Lifecycle

```
        create_watchlist()
              │
              ▼
        ┌─────────┐   pause_watchlist()   ┌────────┐
        │ ACTIVE  │ ────────────────────► │ PAUSED │
        └─────────┘ ◄──────────────────── └────────┘
              │        resume_watchlist()
              │
              │ archive_watchlist()
              ▼
        ┌──────────┐
        │ ARCHIVED │   (terminal; enabled=False, alert evaluation skips it)
        └──────────┘
```

Pausing/archiving a watchlist sets `enabled=False`, so Sprint 10-style
`evaluate_all()`/`AlertRuleService` scans that filter on `enabled=True` skip
it automatically — no separate "is this watchlist paused" check is needed in
alert evaluation code.

## Default watchlist

At most one watchlist per `owner_id` may have `is_default=True`. Creating a
new default watchlist automatically clears the flag on any previous default
for that owner (`ExtendedWatchlistService._clear_default`). The Shopping
Assistant's `add_to_watchlist` uses the default watchlist (falling back to
the first existing watchlist, or creating one) when no `watchlist_id` is
supplied.

## Watchlist history

Every lifecycle transition and item mutation is recorded as a
`WatchlistHistoryEntry` (`event_type`, `description`, `actor_id`, optional
`item_id`/`metadata`), retrievable via `GET /watchlists/{id}/history`. This
powers the recent-activity feed on the [User Dashboard](USER_DASHBOARD.md).
History is in-memory only — no separate audit database exists.

## API

Base paths: `/api/v1/watchlists` and `/api/v1/alerts` (Sprint 10 acknowledge/
dismiss surface — unchanged; rule-driven alerts live under
`/api/v1/alerts/rules` — see [`ALERT_ENGINE.md`](ALERT_ENGINE.md)).

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/watchlists` | Bearer* | filters: `enabled`, `status`; scoped to caller |
| `POST` | `/watchlists` | Bearer* | `is_default` supported |
| `GET` | `/watchlists/{id}` | Bearer* + owner | |
| `PATCH` / `PUT` | `/watchlists/{id}` | Bearer* + owner | |
| `DELETE` | `/watchlists/{id}` | Bearer* + owner | |
| `POST` | `/watchlists/{id}/pause` | Bearer* + owner | Sprint 19 |
| `POST` | `/watchlists/{id}/resume` | Bearer* + owner | Sprint 19 |
| `POST` | `/watchlists/{id}/archive` | Bearer* + owner | Sprint 19 |
| `GET` | `/watchlists/{id}/history` | Bearer* + owner | Sprint 19; `limit` 1–200 |
| `PUT` | `/watchlists/{id}/preferred-sellers` | Bearer* + owner | Sprint 19 |
| `PUT` | `/watchlists/{id}/preferred-marketplaces` | Bearer* + owner | Sprint 19 |
| `GET` / `POST` | `/watchlists/{id}/items` | Bearer* + owner | `POST` uses `add_offer` when `marketplace_offer_id` is set |
| `POST` | `/watchlists/{id}/offers` | Bearer* + owner | Sprint 19 |
| `GET` / `PATCH` / `DELETE` | `/watchlists/{id}/items/{item_id}` | Bearer* + owner | |
| `PUT` | `.../items/{item_id}/preferred-sellers` | Bearer* + owner | Sprint 19 |
| `PUT` | `.../items/{item_id}/preferred-marketplaces` | Bearer* + owner | Sprint 19 |
| `GET` / `POST` | `/watchlists/{id}/alerts`, `.../check-alerts` | Bearer* + owner | Sprint 10 manual evaluation |
| `POST` | `/watchlists/check-alerts` | No | evaluate all enabled watchlists |
| `GET` | `/alerts` | No | Sprint 10 legacy alert list |
| `GET`/`POST` | `/alerts/{id}`, `.../acknowledge`, `.../dismiss` | No | Sprint 10 legacy alerts |

\* Required only when `WATCHLISTS_REQUIRE_AUTH=true` (default).

## Offers vs. products

`WatchlistItem.item_kind` distinguishes:

- `product` (default) — tracks a `canonical_product_id` across marketplaces.
- `offer` — tracks one specific `marketplace_offer_id` (e.g. "this exact
  Shopee listing"), via `add_offer()` / `POST /watchlists/{id}/offers`.

## Limitations

- **In-app functional**; **email is simulated** (see
  [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md)) —
  no real message is ever sent.
- **No SMS. No push.**
- **No external scheduler** — alert/history evaluation is always triggered
  by an explicit API call or test, never a background cron/worker/queue.
- **In-memory persistence only** — `InMemoryWatchlistStore` is process-local;
  restarting the API process discards all watchlists, items, and history.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** anywhere in this feature.
- Ownership enforcement depends on `UserPlatformService`; watchlists created
  before Sprint 17/19 (or via `WATCHLISTS_REQUIRE_AUTH=false`) with
  `owner_id=None` remain accessible to any caller.
- Preferred-seller/marketplace tagging is informational metadata consumed by
  the [Alert Engine](ALERT_ENGINE.md); it does not filter marketplace search
  results anywhere else in the product.
