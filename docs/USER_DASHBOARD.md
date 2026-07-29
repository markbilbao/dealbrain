# User Dashboard (Sprint 19)

**Status:** Sprint 19
**Service:** `UserDashboardService` in `app/services/user_dashboard_service.py`
**Pure assembler:** `app/dashboard/assembler.py`
**Domain entities:** `app/domain/entities/dashboard.py`
**Depends on:** [`WATCHLISTS.md`](WATCHLISTS.md), [`ALERT_ENGINE.md`](ALERT_ENGINE.md), [`NOTIFICATIONS.md`](NOTIFICATIONS.md)

## Overview

The User Dashboard is a read-only, per-user aggregation view: one summary
plus a fixed set of cards drawn from a user's watchlists, alert rules, alert
events, and notifications. It performs **no writes** and triggers **no
evaluation** — it only reads state that was already produced by other
services.

## Architecture

```
GET /api/v1/dashboard
      │
      ▼
UserDashboardService.get_dashboard(user_id)
      │  (all I/O happens here; every collaborator except watchlist_service is optional)
      ├─► WatchlistService / ExtendedWatchlistService  — owned watchlists, items, enrich_item(), get_history()
      ├─► AlertRuleService                              — active rule count
      ├─► AlertRepository (Sprint 10 legacy alerts)      — recent alerts card
      ├─► AlertEventRepository (Sprint 19 events)        — price-drop/restock/better-offer cards, activity
      ├─► NotificationCenterService                      — unread count, notification list
      └─► MarketplaceDataService (optional)               — source-mode-aware freshness note
      │
      ▼
app.dashboard.assembler.assemble_dashboard()      (pure — no I/O)
      ├─ build_summary()             — headline counters + potential_savings
      ├─ build_summary_card()
      ├─ build_recent_alerts_card()
      ├─ build_price_drops_card() / build_restocks_card() / build_better_offers_card()
      ├─ build_stale_data_card()
      ├─ build_watchlists_card()
      └─ build_activity_card()
      │
      ▼
UserDashboard { summary, cards[], recent_activity[], limitations }
```

## Cards

| `DashboardCardType` | Source | Notes |
|----------------------|--------|-------|
| `summary` | `DashboardSummary.to_dict()` | headline counters; `summary` text carries the freshness note |
| `recent_alerts` | Sprint 10 `Alert` records, newest first | legacy alert compatibility |
| `price_drops` | Sprint 19 `AlertEvent`s of type `PRICE_DROP` | |
| `restocks` | `AlertEvent`s of type `RESTOCK` | |
| `better_offers` | `AlertEvent`s of type `BETTER_OFFER` | |
| `stale_data` | `WatchlistItemSnapshot`s with `price_available=False` | |
| `watchlists` | The user's owned watchlists | |
| `activity` | `UserActivity` feed: watchlist history entries + alert events, merged and sorted by time, capped at 20 | |

## Summary counters

`build_summary()` computes, purely from already-fetched collections:
`watched_products`, `active_alert_rules` (enabled rules only),
`unread_notifications`, `recent_price_drops`, `restocked_items`,
`better_offers`, `stale_data_count`, and `potential_savings`.

**`potential_savings`** is a conservative, already-observed figure: for each
watchlist item snapshot where the current price is lower than the item's
last known price, the drop is summed (never counted negative). It is **not**
a projection, a guarantee, or a claim about future pricing — see the
`savings_freshness_note` caveat below, which is always attached alongside
the number.

## Source-mode labels & freshness

Every dashboard summary carries a `savings_freshness_note`, defaulting to:

> "Dashboard figures summarize fixture and imported watchlist/marketplace
> data only; they do not reflect live marketplace pricing."
> (`DASHBOARD_LIMITATIONS_NOTE`, `app/domain/entities/dashboard.py`)

When a `MarketplaceDataService` collaborator is wired in,
`UserDashboardService._freshness_note()` extends this note with the
`SourceMode` labels (`SOURCE_MODE_LABELS`, e.g. "Demo / fixture data — not
live marketplace pricing", "Imported data — not live marketplace pricing",
"Live connector data") backing the marketplace offers currently on record.
Offers flagged `simulated=True` are always resolved through the
`SourceMode.LIVE` label regardless of their own `source_mode` — i.e. a
simulated offer's raw fixture/imported mode is never shown unlabeled — so
callers should treat the presence of any simulated offer as a signal that
the "Live connector data" wording in the note does not imply a real
marketplace connection. If no marketplace collaborator is configured, or
the lookup fails or returns no offers, the base limitations note is used
unchanged — the freshness overlay is strictly best-effort and never raises.

## API

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/dashboard` | Bearer* | Returns `UserDashboardResponse`; includes `personalization` context from `UserPlatformService.shopping_assistant_context()` when available |

\* Falls back to a query-supplied `user_id` only when
`WATCHLISTS_REQUIRE_AUTH=false`.

## Limitations

- **In-app functional; email simulated** — the dashboard itself has no email
  surface, but the notification counts it displays originate from a system
  where email delivery is simulated (see
  [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md)).
- **No SMS. No push.**
- **No external scheduler** — the dashboard is computed synchronously on
  each `GET` request; there is no background refresh job or cache warmer.
- **In-memory persistence only** — every collaborator the dashboard reads
  from (watchlists, alert rules/events, notifications) is in-memory and
  process-local.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** appear anywhere on the dashboard.
- **`potential_savings` is a caveated, already-observed estimate** —
  it is explicitly not a live-pricing guarantee, and the accompanying
  `savings_freshness_note` must always be surfaced alongside the number in
  any UI that renders it.
- Dashboard assembly is read-only and cannot trigger alert evaluation,
  notification digesting, or watchlist mutation as a side effect.
