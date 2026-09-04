# Email Provider Architecture

This document covers two separate email ports. Do not merge them.

## Identity transactional email (Sprint 27.1)

**Port:** `EmailSender` in `app/auth/email.py`  
**Adapters:** `NullEmailSender` (development/test) and `ResendEmailSender` (`app/auth/email_resend.py`)  
**Factory:** `build_identity_email_sender()` in `app/auth/email_factory.py`  
**Templates:** `app/auth/email_templates.py`  
**Runbook:** [`runbooks/EMAIL_OUTAGE.md`](runbooks/EMAIL_OUTAGE.md)

Auth/account code sends only through `EmailSender`. There are no direct Resend
calls in `AuthService` or the auth HTTP layer.

| Environment | Sender | Inline demo tokens |
|-------------|--------|--------------------|
| development | `NullEmailSender` unless `TRANSACTIONAL_EMAIL_PROVIDER=resend` | allowed only if `ALLOW_DEMO_RESET_TOKENS=true` |
| staging | Resend when configured; `NullEmailSender` if provider is still `null` (validation records the gap) | never |
| production | Resend required; factory/startup fail otherwise | never |
| unknown | refuse sender | never |

Configuration (no secrets in git):

- `TRANSACTIONAL_EMAIL_PROVIDER` (`null` \| `resend`)
- `RESEND_API_KEY` (Secrets Manager leaf `resend_api_key`)
- `TRANSACTIONAL_EMAIL_FROM` / `TRANSACTIONAL_EMAIL_FROM_NAME`
- `PUBLIC_APP_BASE_URL` (trusted link base; never request `Host`)

EXT-08 remains `applied` (account establishment). EXT-09 remains `applied`
(DNS plan only). 27.1 does **not** claim sender-domain verification or
production email readiness. Health/config `identity_email_ready` stays
`false` while that evidence is missing — including staging on
`NullEmailSender`.

Sprint 19 notification email below is unchanged and still mock-only.

---

# Notification email (Sprint 19)

**Status:** Sprint 19
**Interface & mock:** `app/notifications/email/provider.py`
**Renderer:** `app/notifications/email/renderer.py`
**Consumer:** `NotificationCenterService` (`app/services/notification_center_service.py`)
**Parent doc:** [`NOTIFICATIONS.md`](NOTIFICATIONS.md)

## Overview

DealBrain defines a clean port/adapter boundary for email delivery so a real
transport (SES, SendGrid, Postmark, raw SMTP, ...) could be wired in later
**without changing any calling code** — but no such adapter exists yet.
The only concrete implementation shipped in this codebase is
`MockEmailNotificationProvider`, which simulates every send and never
performs network I/O.

> **No real provider is configured or connected in Sprint 19.** Every
> "email" produced by this system is a `SIMULATED EMAIL — NO REAL MESSAGE
> SENT` record kept in process memory.

## Architecture

```
NotificationCenterService
      │  (constructor: email_provider: EmailNotificationProvider | None = None)
      │  defaults to MockEmailNotificationProvider if not supplied
      ▼
EmailNotificationProvider (ABC)              ◄── the only extension point
      │  send(message: EmailMessage) -> EmailSendResult
      │
      ├── MockEmailNotificationProvider   (Sprint 19 — the ONLY concrete class)
      │       • never opens a socket / calls an HTTP API
      │       • returns EmailSendResult(simulated=True, detail=<SIMULATED_EMAIL_MARKER ...>)
      │       • records every send in an in-process `sent_messages` list for tests/demo
      │
      └── (future real provider — SES / SendGrid / SMTP — NOT IMPLEMENTED)
              would satisfy the same `send()` signature; no code in
              NotificationCenterService would need to change to adopt one.
```

## Interface contract

```python
class EmailNotificationProvider(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> EmailSendResult:
        """"Send" (simulate sending) an email message and return the result."""
```

- `EmailMessage` — `to_address`, `subject`, `body_text`, `body_html | None`.
  Fully rendered by the caller (`NotificationCenterService._render_event_content`
  / `render_template`); the provider never templates content itself.
- `EmailSendResult` — `message_id`, `to_address`, `subject`, `sent_at`,
  `simulated: bool`, `detail: str`, `metadata: dict[str, str]`.

`EmailNotificationProvider` implementations **must not** perform real network
I/O in this codebase — this is documented directly on the ABC.

## `MockEmailNotificationProvider`

- Every `send()` call appends an `EmailSendResult` to an internal
  `sent_messages` list (readable for tests/demo introspection) and returns
  immediately — no delay, no retries, no network.
- `EmailSendResult.simulated` is always `True`.
- `EmailSendResult.detail` always contains the literal string
  `SIMULATED_EMAIL_MARKER = "SIMULATED EMAIL — NO REAL MESSAGE SENT"`,
  followed by the subject and recipient — this is the single
  machine-checkable guarantee that no real message was sent, and every test
  that exercises email delivery should assert on it.
- `clear()` resets recorded sends (used between test cases sharing a
  provider instance).

## Where email is triggered

1. **Immediate delivery** — `NotificationCenterService._deliver_channels()`
   calls `email_provider.send()` once per notification when
   `prefs.email_enabled=True`, the notification's type/category is allowed,
   and the send is not suppressed by quiet hours /
   `immediate_alerts=False` (see
   [`NOTIFICATION_PREFERENCES.md`](NOTIFICATION_PREFERENCES.md)). Suppressed
   sends are recorded as a `SKIPPED` `NotificationDelivery`, not attempted.
2. **Digest delivery** — `NotificationCenterService.deliver_digest()` calls
   `email_provider.send()` once with an aggregated subject/body when the
   digest `has_content()` and the user has `email_enabled=True`; otherwise
   the digest is marked `DigestStatus.FAILED` and no send is attempted.

Both call sites use `to_address=f"{user_id}@example.invalid"` — the
`.invalid` TLD (RFC 2606) makes it structurally impossible for a
misconfigured real provider to accidentally deliver anywhere.

## Failure handling

`send()` is not wrapped in a `try/except` at the call sites above — a
provider that raises will propagate the exception to the
`create_notification()` / `deliver_digest()` caller. This is intentional:
because the only provider is a mock that never raises in normal operation,
callers today never observe a mid-flight email failure. A future real
provider integration would need to decide (at that time) whether failures
should be caught, retried, or surfaced — this is explicitly **not** decided
by Sprint 19. Because the in-app `Notification` row is always saved *before*
`_deliver_channels()` runs, an email-provider failure never prevents the
notification from existing in the user's inbox; only the email side effect
is at risk.

## Digest content marking

`app/notifications/digest/builder.py` exposes `mark_simulated(digest)` and
`mark_failed(digest)`, which set `NotificationDigest.status` to
`DigestStatus.SIMULATED` or `DigestStatus.FAILED` respectively, plus a
`simulated_email_detail` string on the digest itself — so even digest
records at rest are unambiguously labeled as non-real deliveries.

## Limitations

- **No real email provider is implemented or configured** — SMTP, SES,
  SendGrid, Postmark, Mailgun, etc. integrations do not exist in this
  codebase.
- **Email is simulated end-to-end.** No message ever leaves the process;
  there is no outbound network call anywhere in `app/notifications/email/`.
- **No SMS. No push.** This document covers only the email channel; no
  parallel provider interface exists for either.
- **No external scheduler** drives digest delivery — `deliver_digest()` is
  only invoked explicitly.
- **In-memory persistence only** for delivery records
  (`NotificationDelivery`) and digests.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** appear in any rendered email template.
- Recipient addresses are synthetic (`{user_id}@example.invalid`) — real
  user email addresses are never read from or written to this subsystem.
