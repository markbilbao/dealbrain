# Notification Preferences (Sprint 19)

**Status:** Sprint 19
**Service:** `NotificationPreferenceService` in `app/services/notification_preference_service.py`
**Helpers:** `app/notifications/preferences.py`
**Entity:** `UserNotificationPreferences` in `app/domain/entities/notifications.py`
**Parent doc:** [`NOTIFICATIONS.md`](NOTIFICATIONS.md)

## Overview

Every user has exactly one `UserNotificationPreferences` record, lazily
created with safe, **opt-in-only** defaults the first time it is read. There
is no separate "preferences setup wizard" — `get_preferences()` transparently
creates and persists the default record on first access.

## Architecture

```
NotificationCenterService._deliver_channels() / build_daily_digest() / build_weekly_digest()
      │
      ▼
NotificationPreferenceService
      ├─ get_preferences(user_id)            — lazy-create UserNotificationPreferences
      ├─ update_preferences(user_id, **kw)   — partial update; quiet-hours fields
      │                                         support an explicit "clear to None" sentinel
      ├─ is_quiet_hours(user_id, now=...)
      ├─ should_suppress_immediate(user_id, now=...)
      └─ channel_enabled(user_id, channel)
              │
              ▼
      app.notifications.preferences (pure functions)
              ├─ default_preferences()
              ├─ is_within_quiet_hours()          — supports overnight windows (e.g. 22:00→07:00)
              ├─ should_suppress_immediate_alert() — immediate_alerts=False OR inside quiet hours
              └─ channel_enabled()
              │
              ▼
      InMemoryNotificationCenterRepository.get/save_preferences()
```

## Preference fields

| Field | Default | Purpose |
|-------|---------|---------|
| `in_app_enabled` | `True` | Master toggle for the in-app channel |
| `email_enabled` | `False` | Master toggle for the (simulated) email channel |
| `immediate_alerts` | `True` | Deliver alert-triggered notifications as soon as they fire |
| `daily_digest` | `False` | Opt in to a daily rollup email |
| `weekly_digest` | `False` | Opt in to a weekly rollup email |
| `quiet_hours_start` / `quiet_hours_end` | `None` | `"HH:MM"` local-time window during which immediate alerts are suppressed (wraps past midnight) |
| `timezone` | `"UTC"` | Informational; quiet-hours comparisons operate on caller-supplied local time |
| `price_alerts` / `stock_alerts` / `freshness_warnings` | `True` | Coarse per-category opt-outs |
| `marketing_enabled` | **`False`** | Marketing/promotional messages — **opt-in only** |

## Quiet hours

`is_within_quiet_hours()` compares `now.time()` (already assumed to be in
the user's local time — no timezone conversion is performed inside the
helper) against the `[quiet_hours_start, quiet_hours_end)` window, correctly
handling windows that wrap past midnight (e.g. `22:00` → `07:00`). No quiet
hours are configured by default, so no notification is ever silently delayed
unless the user has explicitly set both fields.

`should_suppress_immediate_alert()` suppresses an immediate send when either:

1. `immediate_alerts` is disabled outright, or
2. `now` falls inside the configured quiet-hours window.

A suppressed immediate alert is **not dropped** — the underlying alert event
and in-app notification are still created; the caller is expected to route
suppressed items to the next digest instead of an immediate email send.

## Digests

`daily_digest` / `weekly_digest` are independent opt-in flags consumed by
`NotificationCenterService.build_daily_digest()` /
`build_weekly_digest()` (see [`NOTIFICATIONS.md`](NOTIFICATIONS.md)). Digest
emails, like immediate alerts, are simulated — see
[`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md).

## Marketing is opt-in only

`marketing_enabled` defaults to `False` for every new user
(`default_preferences()` sets it explicitly, mirroring the entity's own
default) and is **only** ever changed by an explicit
`update_preferences(marketing_enabled=...)` call — no other preference
change, digest build, or notification delivery path implicitly flips it on.
There is currently no marketing/promotional notification type wired up to
actually use this flag; it exists as forward-looking, explicitly-gated
plumbing.

## API

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/notifications/preferences` | Bearer* | Lazily creates defaults on first call |
| `PUT` | `/notifications/preferences` | Bearer* | Partial update; `clear_quiet_hours_start` / `clear_quiet_hours_end` flags explicitly null out a window boundary (distinct from omitting the field, which leaves it unchanged) |

\* Falls back to a query/body-supplied `user_id` only when
`WATCHLISTS_REQUIRE_AUTH=false`.

## Limitations

- **In-app functional; email simulated** — enabling `email_enabled` routes
  through the mock provider only; see
  [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md).
- **No SMS. No push.** There are no corresponding preference fields for
  either channel.
- **No external scheduler** — digest preferences only take effect when a
  digest is explicitly built/delivered by a caller.
- **In-memory persistence only** — preferences live in
  `InMemoryNotificationCenterRepository` for the life of the process.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** — and no marketing content is ever generated even when
  `marketing_enabled=True`, since no marketing notification producer exists
  yet.
- **Marketing is disabled by default** and requires an explicit, separate
  opt-in action.
