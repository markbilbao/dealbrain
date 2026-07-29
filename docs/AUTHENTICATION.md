# Authentication

**Status:** Sprint 17
**Service:** `AuthService` in `app/auth/service.py`
**Password hashing:** `app/auth/password.py` (`PasswordHasher`)
**Security hooks:** `app/auth/security.py` (rate limiting, CSRF, audit, MFA/OAuth extension points)
**Email port:** `app/auth/email.py` (`NullEmailSender` — no delivery)

## Overview

`AuthService` implements register, login, logout, and session validation for
demo/in-memory DealBrain accounts. It composes password hashing, rate
limiting, audit logging, and no-op extension points for MFA and OAuth so the
architecture is ready for those features without implementing them in
Sprint 17.

## Registration

`POST /api/v1/auth/register` → `AuthService.register(email, password, display_name, remember_me=False)`

Validation:

- `email` must match a basic `user@domain.tld` shape (normalized to lowercase, trimmed).
- `password` must be at least 8 characters, include mixed case, and include at least one digit.
- `display_name` must not be blank.
- Registration is rate-limited per normalized email (`RateLimiterHook`, 20 attempts / 60s window by default).
- Duplicate emails raise `UserPlatformConflictError` (HTTP 409).

On success, a `User` is created, a starter `UserProfile` + `UserSettings` are
bootstrapped (`AuthService._bootstrap_profile`), a `SecurityEvent` is recorded,
and a session is issued — see [Session Management](SESSION_MANAGEMENT.md).

## Login

`POST /api/v1/auth/login` → `AuthService.login(email, password, remember_me=False)`

- Rate-limited per normalized email.
- Unknown email, inactive account, or bad password all raise the same
  generic `UserPlatformAuthError("Invalid email or password.")` (HTTP 401) to
  avoid account enumeration.
- If `MfaExtensionPoint.is_enabled(user_id)` ever returns `True` (it does not
  in Sprint 17), login raises `UserPlatformAuthError("MFA required but not
  implemented in Sprint 17.")` rather than silently bypassing MFA.
- On success, the rate limiter is reset for that email and a new session is issued.

## Logout

`POST /api/v1/auth/logout` → `AuthService.logout(access_token)`

Revokes the session backing the provided bearer token. Missing/invalid
tokens are a no-op (idempotent logout); no error is raised.

## Password hashing

`PasswordHasher` (`app/auth/password.py`) uses PBKDF2-HMAC-SHA256 from the
Python standard library — no third-party crypto dependency, no hardcoded
secrets. Hashes are stored as `pbkdf2_sha256$<iterations>$<salt-hex>$<digest-hex>`
so the algorithm can be migrated (e.g. to argon2 or bcrypt) later without
breaking existing hashes. Verification uses `hmac.compare_digest` for
constant-time comparison.

## Password reset & email verification (architecture only)

`AuthService.request_password_reset(email)` and
`AuthService.request_email_verification(user_id)` create hashed,
time-bounded token records (`PasswordResetRequest`, `EmailVerificationRequest`)
and route a message through `EmailSender`. In Sprint 17, the only
implementation is `NullEmailSender`, which records the message in memory and
sends nothing. Responses include the raw token under a
`*_token_demo_only` key purely so the flow is testable without an inbox —
**this must not ship in a real deployment**.

## MFA and OAuth extension points

`MfaExtensionPoint` and `OAuthExtensionPoint` (`app/auth/security.py`) define
the shape of future multi-factor and external-identity-provider support.
Both are inert in Sprint 17: `MfaExtensionPoint.is_enabled()` always returns
`False`, and `OAuthExtensionPoint.begin_link()` always returns
`status: "not_implemented"`.

## Bearer tokens

Sessions are opaque, high-entropy random tokens (`secrets.token_urlsafe`),
returned once at register/login time. Only a SHA-256 hash of the token
(`AuthService.hash_token`) is ever persisted server-side — the raw token
cannot be recovered from storage. Clients must send it as:

```
Authorization: Bearer <access_token>
```

The API layer's `extract_bearer_token()` helper
(`app/api/v1/endpoints/auth.py`) parses this header; a missing or malformed
header is treated as an unauthenticated request.

## Error mapping

| Domain exception | HTTP status | Example |
|--------------------|-------------|---------|
| `UserPlatformValidationError` | 400 | Weak password, malformed email |
| `UserPlatformAuthError` | 401 | Bad credentials, expired/revoked session |
| `UserPlatformConflictError` | 409 | Email already registered |
| `UserPlatformRateLimitError` | 429 | Too many register/login attempts |

## Limitations

- **Demo users only** — no production account provisioning flow.
- **No email sending** — reset/verification tokens are returned inline for
  demo purposes instead of being emailed.
- **No MFA** implemented — extension point only.
- **No OAuth / external identity providers** — extension point only.
- **In-memory persistence only** — accounts and sessions reset on restart.
- **No production database adapter** wired in Sprint 17.
- **No payment integration.**
