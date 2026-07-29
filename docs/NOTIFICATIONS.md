# Notification Center (Sprint 19)

**Status:** Sprint 19
**Service:** `NotificationCenterService` in `app/services/notification_center_service.py`
**Domain entities:** `app/domain/entities/notifications.py`
**Repository port:** `app/domain/interfaces/notification_center_repository.py`
**In-memory store:** `InMemoryNotificationCenterRepository` in `app/notifications/memory.py`
**Digest builder:** `app/notifications/digest/builder.py`
**Email architecture:** [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md)
**Preferences:** [`NOTIFICATION_PREFERENCES.md`](NOTIFICATION_PREFERENCES.md)

## Overview

The Notification Center is DealBrain's per-user inbox for alert-driven and
system messages. It is deliberately narrower than a general messaging
platform: **one functional channel (in-app) plus one architecturally-complete
but simulated channel (email)**. There is no SMS and no push notification
support anywhere in the codebase.

## Architecture

```
AlertEvaluationService / AlertService (legacy)
      │  create_from_alert_event() / _notify_notification_center()
      ▼
NotificationCenterService
      ├─ create_notification()          — persists a Notification, applies user type/severity filtering
      ├─ _type_allowed()                ──► NotificationPreferenceService (per-type opt-out)
      ├─ _deliver_channels()
      │     ├─ IN_APP   → always recorded (this *is* the notification record itself)
      │     └─ EMAIL    → EmailNotificationProvider.send()  (MockEmailNotificationProvider — SIMULATED)
      ├─ _record_delivery()             — NotificationDelivery audit row per channel attempt
      ├─ list/get/mark_read/mark_all_read/archive/delete()
      ├─ create/validate/revoke_unsubscribe_token(), unsubscribe()
      └─ build_daily_digest() / build_weekly_digest() / deliver_digest()
              └─► app.notifications.digest.builder (pure selection/aggregation)
                        └─► EmailNotificationProvider.send() (digest email — SIMULATED)
      │
      ▼
InMemoryNotificationCenterRepository  (notifications, deliveries, templates, digests, preferences, unsub tokens)
```

## Notification lifecycle

```
create_notification()
        │
        ▼
   ┌─────────┐  mark_read()   ┌──────┐
   │ UNREAD  │ ─────────────► │ READ │
   └─────────┘                └──────┘
        │                         │
        │ archive()                │ archive()
        ▼                         ▼
                 ┌──────────┐
                 │ ARCHIVED │
                 └──────────┘
        (any state) ── delete() ──► removed from store
```

`mark_all_read()` transitions every `UNREAD` notification for a user to
`READ` in one call and returns the count updated.

## Notification types & severity

`NotificationType` covers all Sprint 19 alert conditions
(`PRICE_DROP`, `PRICE_INCREASE`, `RESTOCK`, `OUT_OF_STOCK`, `LOW_INVENTORY`,
`BETTER_OFFER`, `DEALSCORE_THRESHOLD`, `FRESHNESS_WARNING`, `DIGEST`,
`SYSTEM`, ...). `NotificationSeverity` (`INFO`/`WARNING`/`CRITICAL`) is
derived from the triggering `AlertEvent`'s `AlertSeverity`. Per-user,
per-type suppression is enforced by
[`NOTIFICATION_PREFERENCES.md`](NOTIFICATION_PREFERENCES.md) before a
notification is created at all — disabled types never appear in the list,
not even as a read/dismissed row.

## Channels

| Channel | Status | Notes |
|---------|--------|-------|
| `IN_APP` | **Functional** | The notification row itself; always the source of truth for `list_notifications`/`unread_count`. |
| `EMAIL` | **Architecture-complete, simulated** | Routed through `EmailNotificationProvider`; `MockEmailNotificationProvider` never contacts a real mail server. Every simulated send is tagged with the `SIMULATED EMAIL — NO REAL MESSAGE SENT` marker. See [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md). |
| SMS | **Not implemented** | No `NotificationChannel.SMS` delivery path exists. |
| Push | **Not implemented** | No push/APNs/FCM integration exists. |

Every delivery attempt (success or failure) is recorded as a
`NotificationDelivery` row (`channel`, `status`, `provider_message_id`,
`error`), independent of channel — so a failed simulated-email delivery is
still visible in delivery history even though the in-app notification itself
was created successfully.

## Digests

`app/notifications/digest/builder.py` provides pure functions
(`select_pending_notifications`, `build_daily_digest`, `build_weekly_digest`)
that aggregate a user's undelivered notifications for a `DigestPeriod`
(`DAILY`/`WEEKLY`) into one `NotificationDigest`. `NotificationCenterService`
wraps these with persistence (`save_digest`) and delivery
(`deliver_digest()` → simulated email via `EmailNotificationProvider`).
Digests are **built and sent on demand only** — there is no background
scheduler that fires them automatically (consistent with the
[Alert Engine](ALERT_ENGINE.md)'s no-external-scheduler design). A digest
with no eligible notifications reports `has_content() == False` and is not
sent.

## Unsubscribe tokens

`create_unsubscribe_token()` issues a hashed, single-purpose token
(`UnsubscribeToken`, only `token_hash` persisted) scoped to a notification
type or "all". `validate_unsubscribe_token()` / `unsubscribe()` /
`revoke_unsubscribe_token()` let a one-click email footer link disable future
notifications without requiring a login. This is used only by the simulated
email templates — no real link is ever emailed to a real inbox.

## API

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/notifications` | Bearer* | filters: `status`, `type`, pagination |
| `GET` | `/notifications/unread-count` | Bearer* | |
| `POST` | `/notifications/mark-all-read` | Bearer* | |
| `POST` | `/notifications/{id}/read` | Bearer* + owner | |
| `POST` | `/notifications/{id}/archive` | Bearer* + owner | |
| `DELETE` | `/notifications/{id}` | Bearer* + owner | |
| `GET` | `/notifications/preferences` | Bearer* | see [`NOTIFICATION_PREFERENCES.md`](NOTIFICATION_PREFERENCES.md) |
| `PUT` | `/notifications/preferences` | Bearer* | |

\* Falls back to a query/body-supplied `user_id` only when
`WATCHLISTS_REQUIRE_AUTH=false`.

## Limitations

- **In-app is functional.** **Email is simulated** — every "sent" email is a
  `MockEmailNotificationProvider` record tagged
  `SIMULATED EMAIL — NO REAL MESSAGE SENT`; no SMTP/API call ever leaves the
  process.
- **No SMS. No push.**
- **No external scheduler** — digests and evaluations are only produced by
  an explicit call.
- **In-memory persistence only** — all notifications, deliveries, digests,
  and unsubscribe tokens live in `InMemoryNotificationCenterRepository` for
  the life of the process.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** anywhere in this feature.
- **Marketing notifications are opt-in and disabled by default** — see
  [`NOTIFICATION_PREFERENCES.md`](NOTIFICATION_PREFERENCES.md).
